"""
db_client.py
Supabase-py client with salon booking functions.

Functions:
    get_services()              → list all active services
    get_service(service_id)     → single service by id
    get_free_slots(service_id, date, staff_id?) → available 30-min slots
    book_appointment(phone, name, service_id, start_time) → book & return row
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_working_hours(day_of_week: int) -> dict | None:
    """Return {start, end} times for a given day (0=Sun … 6=Sat)."""
    rows = (
        sb.table("working_hours")
        .select("start_time, end_time")
        .eq("day_of_week", day_of_week)
        .execute()
    )
    return rows.data[0] if rows.data else None


def _get_existing_appointments(staff_id: int, date_str: str) -> list:
    """Fetch confirmed appointments for a staff member on a given date."""
    start_of_day = f"{date_str}T00:00:00"
    end_of_day = f"{date_str}T23:59:59"
    rows = (
        sb.table("appointments")
        .select("start_time, end_time")
        .eq("staff_id", staff_id)
        .eq("status", "confirmed")
        .gte("start_time", start_of_day)
        .lte("start_time", end_of_day)
        .execute()
    )
    return rows.data or []


# ── public API ────────────────────────────────────────────────────────────────

def get_or_create_customer(phone: str, name: str | None = None) -> int:
    """
    Look up a customer by phone number.
    - If found AND a non-empty `name` is provided that differs from the stored
      name, UPDATE the customer record to the latest name.
    - If found AND `name` is None/empty, leave the existing name untouched.
    - If not found, INSERT a new row (name is required in that case).
    Returns the customer id.
    """
    rows = sb.table("customers").select("id, name").eq("phone", phone).execute().data

    if rows:
        customer_id = rows[0]["id"]
        existing_name = rows[0].get("name")
        if name and name != existing_name:
            sb.table("customers").update({"name": name}).eq("id", customer_id).execute()
            print(f"[db_client] Updated customer #{customer_id} name: {existing_name!r} -> {name!r}")
        return customer_id

    # New customer — name is required
    if not name:
        raise ValueError("A name is required when creating a new customer")
    inserted = sb.table("customers").insert({"phone": phone, "name": name}).execute()
    customer_id = inserted.data[0]["id"]
    print(f"[db_client] Created new customer #{customer_id}: {name!r} ({phone})")
    return customer_id


def get_services() -> list[dict]:
    """Return all active services."""
    rows = (
        sb.table("services")
        .select("*")
        .eq("active", True)
        .order("id")
        .execute()
    )
    services = rows.data or []
    print(f"[db_client] get_services => {len(services)} services")
    return services


def get_service(service_id: int) -> dict | None:
    """Return a single service by id."""
    rows = (
        sb.table("services")
        .select("*")
        .eq("id", service_id)
        .execute()
    )
    return rows.data[0] if rows.data else None


def get_free_slots(service_id: int, date_str: str, staff_id: int = None) -> list[str]:
    """
    Return available start-time slots (HH:MM strings) for a service on a date.
    Slots are generated in 30-minute increments within working hours.
    If staff_id is given, only that staff is checked; otherwise all staff are
    checked and a slot is "free" only if at least one staff member is available.
    """
    service = get_service(service_id)
    if not service:
        print(f"[db_client] Service {service_id} not found")
        return []

    dt = datetime.strptime(date_str, "%Y-%m-%d")
    # day_of_week: 0=Monday ... 6=Sunday (matches Python's weekday())
    table_day = dt.weekday()

    wh = _get_working_hours(table_day)
    if not wh:
        print(f"[db_client] No working hours for day {table_day}")
        return []

    duration = service["duration_minutes"]

    # Parse working-hours times
    wh_start = datetime.strptime(wh["start_time"], "%H:%M:%S").time()
    wh_end = datetime.strptime(wh["end_time"], "%H:%M:%S").time()

    # Staff to check
    if staff_id:
        staff_ids = [staff_id]
    else:
        staff_rows = sb.table("staff").select("id").eq("active", True).execute().data or []
        staff_ids = [s["id"] for s in staff_rows]

    # Generate candidate 30-min slot start times
    slot_starts = []
    current = datetime.combine(dt, wh_start)
    end_limit = datetime.combine(dt, wh_end)
    while current + timedelta(minutes=duration) <= end_limit:
        slot_starts.append(current)
        current += timedelta(minutes=30)

    # Filter out past slots (if date == today)
    now = datetime.now()
    if dt.date() == now.date():
        slot_starts = [s for s in slot_starts if s > now]

    free_slots = []
    for slot_start in slot_starts:
        slot_end = slot_start + timedelta(minutes=duration)
        slot_available_for_any_staff = False

        for sid in staff_ids:
            existing = _get_existing_appointments(sid, date_str)
            conflict = False
            for appt in existing:
                a_start = datetime.fromisoformat(appt["start_time"])
                a_end = datetime.fromisoformat(appt["end_time"])
                # Overlap check
                if slot_start < a_end and slot_end > a_start:
                    conflict = True
                    break
            if not conflict:
                slot_available_for_any_staff = True
                break

        if slot_available_for_any_staff:
            free_slots.append(slot_start.strftime("%H:%M"))

    print(f"[db_client] get_free_slots({service_id}, {date_str}) => {len(free_slots)} slots: {free_slots}")
    return free_slots


def book_appointment(
    phone: str,
    name: str,
    service_id: int,
    start_time_str: str,   # "2026-08-29 14:00"
    staff_id: int = None,
) -> dict:
    """
    Book a confirmed appointment.
    - Upserts customer by phone.
    - Assigns first available staff if staff_id not given.
    - Returns the created appointment row or raises on conflict.
    """
    service = get_service(service_id)
    if not service:
        raise ValueError(f"Service {service_id} not found")

    # ── upsert customer ───────────────────────────────────────────────────────
    customer_id = get_or_create_customer(phone, name)

    # ── resolve staff ─────────────────────────────────────────────────────────
    if not staff_id:
        staff_rows = sb.table("staff").select("id").eq("active", True).execute().data or []
        if not staff_rows:
            raise RuntimeError("No active staff available")
        staff_id = staff_rows[0]["id"]

    # ── compute end time ──────────────────────────────────────────────────────
    start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
    end_dt = start_dt + timedelta(minutes=service["duration_minutes"])

    # ── insert appointment (exclusion constraint guards against double-booking) ─
    appt = {
        "customer_id": customer_id,
        "staff_id": staff_id,
        "service_id": service_id,
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "status": "confirmed",
        "customer_name_snapshot": name,
    }

    try:
        result = sb.table("appointments").insert(appt).execute()
        booked = result.data[0]
        print(f"[db_client] Booked appointment #{booked['id']} | "
              f"staff={staff_id} | {start_time_str} -> {end_dt.strftime('%H:%M')}")
        return booked
    except Exception as e:
        print(f"[db_client] Booking failed (possible double-booking): {e}")
        raise


# ── quick test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== get_services() ===")
    svcs = get_services()
    for s in svcs:
        print(f"  [{s['id']}] {s['name']} — {s['duration_minutes']}min — Rs.{s['price']}")

    if svcs:
        sid = svcs[0]["id"]
        print(f"\n=== get_service({sid}) ===")
        print(f"  {get_service(sid)}")

        today = datetime.now().strftime("%Y-%m-%d")
        print(f"\n=== get_free_slots(service_id={sid}, date={today}) ===")
        slots = get_free_slots(sid, today)
        print(f"  Slots: {slots}")


# ── cancel booking ───────────────────────────────────────────────────────────

def get_customer_appointments(phone: str) -> list[dict]:
    """Return this customer's own upcoming confirmed appointments."""
    customer = sb.table("customers").select("id").eq("phone", phone).execute()
    if not customer.data:
        return []
    customer_id = customer.data[0]["id"]

    res = sb.table("appointments") \
        .select("id, start_time, end_time, status, customer_name_snapshot, services(name, price)") \
        .eq("customer_id", customer_id) \
        .eq("status", "confirmed") \
        .order("start_time") \
        .execute()

    return [
        {
            "id": appt["id"],
            "customer_name": appt.get("customer_name_snapshot") or "Customer",
            "service": appt["services"]["name"] if appt.get("services") else "Unknown",
            "price": appt["services"]["price"] if appt.get("services") else None,
            "start_time": appt["start_time"],
        }
        for appt in res.data
    ]


def cancel_appointment(phone: str, appointment_id: str) -> dict:
    """Cancel an appointment — ONLY if it belongs to this phone number."""
    customer = sb.table("customers").select("id").eq("phone", phone).execute()
    if not customer.data:
        raise ValueError("No customer found with this phone number")
    customer_id = customer.data[0]["id"]

    appt = sb.table("appointments").select("id, customer_id, status") \
        .eq("id", appointment_id).execute()
    if not appt.data:
        raise ValueError("Appointment not found")

    if appt.data[0]["customer_id"] != customer_id:
        raise ValueError("Appointment not found")

    if appt.data[0]["status"] == "cancelled":
        raise ValueError("This appointment is already cancelled")

    sb.table("appointments").update({"status": "cancelled"}).eq("id", appointment_id).execute()

    return {"id": appointment_id, "status": "cancelled"}


# ── reschedule booking ───────────────────────────────────────────────────────

def reschedule_appointment(phone: str, appointment_id: str, new_start_time: datetime) -> dict:
    """Reschedule an appointment — ONLY if it belongs to this phone number."""
    customer = sb.table("customers").select("id").eq("phone", phone).execute()
    if not customer.data:
        raise ValueError("No customer found with this phone number")
    customer_id = customer.data[0]["id"]

    appt = sb.table("appointments").select("id, customer_id, service_id, staff_id, status") \
        .eq("id", appointment_id).execute()
    if not appt.data:
        raise ValueError("Appointment not found")

    appt_row = appt.data[0]
    if appt_row["customer_id"] != customer_id:
        raise ValueError("Appointment not found")

    if appt_row["status"] != "confirmed":
        raise ValueError("Only confirmed appointments can be rescheduled")

    service = get_service(appt_row["service_id"])
    if not service:
        raise ValueError("Service not found")

    new_end_time = new_start_time + timedelta(minutes=service["duration_minutes"])

    q = sb.table("appointments").select("id").eq("status", "confirmed") \
        .lt("start_time", new_end_time.isoformat()).gt("end_time", new_start_time.isoformat()) \
        .neq("id", appointment_id)
    if appt_row["staff_id"]:
        q = q.eq("staff_id", appt_row["staff_id"])
    conflict = q.execute()
    if conflict.data:
        raise ValueError("New slot is not available")

    sb.table("appointments").update({
        "start_time": new_start_time.isoformat(),
        "end_time": new_end_time.isoformat(),
    }).eq("id", appointment_id).execute()

    return {
        "id": appointment_id,
        "service": service["name"],
        "new_start_time": new_start_time.isoformat(),
        "new_end_time": new_end_time.isoformat(),
        "status": "confirmed",
    }


# ── reminders ─────────────────────────────────────────────────────────────────

def get_pending_reminders() -> list[dict]:
    """Appointments jinki start_time agle 60 minutes mein hai,
    status='confirmed', aur reminder abhi tak nahi bheja gaya."""
    now = datetime.now()
    window_end = now + timedelta(minutes=60)

    res = sb.table("appointments") \
        .select("id, start_time, customer_name_snapshot, customers(phone), services(name)") \
        .eq("status", "confirmed") \
        .eq("reminder_sent", False) \
        .gte("start_time", now.isoformat()) \
        .lte("start_time", window_end.isoformat()) \
        .execute()

    return [
        {
            "appointment_id": appt["id"],
            "customer_name": appt.get("customer_name_snapshot") or "Customer",
            "customer_phone": appt["customers"]["phone"] if appt.get("customers") else None,
            "service": appt["services"]["name"] if appt.get("services") else "Unknown",
            "start_time": appt["start_time"],
        }
        for appt in res.data
    ]


def mark_reminder_sent(appointment_id: str) -> dict:
    """Reminder bhej diye jane ke baad mark karo, dobara na bheje."""
    sb.table("appointments").update({"reminder_sent": True}).eq("id", appointment_id).execute()
    return {"id": appointment_id, "reminder_sent": True}
