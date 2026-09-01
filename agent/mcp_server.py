"""
mcp_server.py
FastMCP stdio server exposing salon booking tools for OpenClaw.

Start:   python mcp_server.py
Connect: openclaw mcp add --name salon -- python /path/to/mcp_server.py

Tools exposed:
    get_services         → list all salon services
    check_availability   → free slots for a service on a date
    book_appointment     → confirm a booking
"""

from datetime import datetime
import json
import logging
import os
from functools import wraps

from fastmcp import FastMCP
import db_client

mcp = FastMCP("Salon Booking")

# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("salon_mcp")
logger.setLevel(logging.DEBUG)

_fh = logging.FileHandler(os.path.join(LOG_DIR, "tool-calls.log"), encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(_fh)


def log_tool(fn):
    """Decorator: logs tool input → output/error without changing logic."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        params = {**kwargs}
        if args:
            import inspect
            sig = inspect.signature(fn)
            for name, val in zip(sig.parameters, args):
                params[name] = val
        logger.info("CALL %s | params=%s", fn.__name__, json.dumps(params, default=str))
        try:
            result = fn(*args, **kwargs)
            if isinstance(result, dict) and "error" in result:
                logger.error("FAIL %s | %s", fn.__name__, json.dumps(result, default=str))
            else:
                logger.info("OK   %s | %s", fn.__name__, json.dumps(result, default=str))
            return result
        except Exception as exc:
            logger.error("CRASH %s | %s: %s", fn.__name__, type(exc).__name__, exc)
            raise
    return wrapper


# ── Tool 1: list services ────────────────────────────────────────────────────

@mcp.tool()
@log_tool
def get_services() -> list[dict]:
    """
    Get all available salon services with name, duration, and price.
    Use this first so the user can pick a service before booking.
    """
    services = db_client.get_services()
    if not services:
        return [{"message": "No services available right now."}]

    result = []
    for s in services:
        result.append({
            "id": s["id"],
            "name": s["name"],
            "duration_minutes": s["duration_minutes"],
            "price": float(s["price"]),
            "description": s.get("description", ""),
        })
    return result


# ── Tool 2: check availability ────────────────────────────────────────────────

@mcp.tool()
@log_tool
def check_availability(service_id: int, date: str) -> dict:
    """
    Check available time slots for a given service on a specific date.
    
    Args:
        service_id: ID of the service (get from get_services tool).
        date:       Date in YYYY-MM-DD format.
    
    Returns list of free time slots (HH:MM) that the customer can choose.
    """
    # Validate date
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    service = db_client.get_service(service_id)
    if not service:
        return {"error": f"Service with id {service_id} not found."}

    slots = db_client.get_free_slots(service_id, date)

    if not slots:
        return {
            "service": service["name"],
            "date": date,
            "available_slots": [],
            "message": f"No free slots for '{service['name']}' on {date}. Try another date.",
        }

    return {
        "service": service["name"],
        "date": date,
        "duration_minutes": service["duration_minutes"],
        "available_slots": slots,
        "message": f"Pick one of these slots for '{service['name']}' on {date}.",
    }


# ── Tool 3: book appointment ─────────────────────────────────────────────────

@mcp.tool()
@log_tool
def book_appointment(
    phone: str,
    name: str,
    service_id: int,
    start_time: str,
) -> dict:
    """
    Book a salon appointment. This confirms the slot and prevents double-booking.
    
    Args:
        phone:      Customer phone number (e.g. '9876543210').
        name:       Customer name.
        service_id: Service ID from get_services.
        start_time: Appointment start as 'YYYY-MM-DD HH:MM' (e.g. '2026-08-29 14:00').
    
    Returns the booked appointment details or an error message.
    """
    # Validate start_time
    try:
        datetime.strptime(start_time, "%Y-%m-%d %H:%M")
    except ValueError:
        return {"error": "Invalid start_time format. Use 'YYYY-MM-DD HH:MM'."}

    service = db_client.get_service(service_id)
    if not service:
        return {"error": f"Service with id {service_id} not found."}

    try:
        appt = db_client.book_appointment(
            phone=phone,
            name=name,
            service_id=service_id,
            start_time_str=start_time,
        )
        return {
            "success": True,
            "appointment_id": appt["id"],
            "customer_name": name,
            "service": service["name"],
            "start_time": start_time,
            "message": f"Appointment #{appt['id']} confirmed for {name} — {service['name']} at {start_time}.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Booking failed. The slot may already be taken. Try another time.",
        }


# ── Tool 4: get my appointments ──────────────────────────────────────────────

@mcp.tool()
@log_tool
def get_my_appointments(customer_phone: str) -> dict:
    """List this customer's own upcoming confirmed appointments. Call
    this first when a customer asks to cancel."""
    appointments = db_client.get_customer_appointments(customer_phone)
    return {"appointments": appointments}


# ── Tool 5: cancel appointment ───────────────────────────────────────────────

@mcp.tool()
@log_tool
def cancel_appointment(customer_phone: str, appointment_id: str) -> dict:
    """Cancel a confirmed appointment. Only cancels if it belongs to
    this customer's phone number — call get_my_appointments first and
    confirm with the customer before calling this."""
    try:
        return db_client.cancel_appointment(customer_phone, appointment_id)
    except ValueError as e:
        return {"error": str(e)}


# ── Tool 6: reschedule appointment ───────────────────────────────────────────

@mcp.tool()
@log_tool
def reschedule_appointment(customer_phone: str, appointment_id: str, new_start_time: str) -> dict:
    """Move an existing confirmed appointment to a new date/time. Only
    works if it belongs to this customer AND the new slot is free.
    Call get_my_appointments first to find appointment_id, and
    check_availability to confirm new slot is open."""
    try:
        new_start = datetime.fromisoformat(new_start_time)
        return db_client.reschedule_appointment(customer_phone, appointment_id, new_start)
    except ValueError as e:
        return {"error": str(e)}


# ── Tool 7: pending reminders ───────────────────────────────────────────────

@mcp.tool()
@log_tool
def get_pending_reminders() -> dict:
    """Check for confirmed appointments starting within the next 60
    minutes that haven't had a reminder sent yet."""
    reminders = db_client.get_pending_reminders()
    return {"pending_reminders": reminders}


# ── Tool 8: mark reminder sent ────────────────────────────────────────────────

@mcp.tool()
@log_tool
def mark_reminder_sent(appointment_id: str) -> dict:
    """Mark that a reminder has been sent for this appointment."""
    return db_client.mark_reminder_sent(appointment_id)


# ── Run server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[mcp_server] Starting Salon Booking MCP server (stdio)...")
    mcp.run(transport="stdio")
