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
from fastmcp import FastMCP
import db_client

mcp = FastMCP("Salon Booking")


# ── Tool 1: list services ────────────────────────────────────────────────────

@mcp.tool()
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


# ── Run server ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[mcp_server] Starting Salon Booking MCP server (stdio)...")
    mcp.run(transport="stdio")
