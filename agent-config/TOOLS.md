# TOOLS.md - Local Notes

## Salon Booking (salon-booking MCP server)
- `get_services` — live list of services, prices, durations from Supabase. Always call fresh, never memorize.
- `check_availability(service_id, date)` — free slots for a service on a date (YYYY-MM-DD).
- `book_appointment(customer_phone, customer_name, service_id, start_time)` — creates the appointment. Only after customer confirms.
- Server location: `C:\Users\SDC\salon-mcp-db\mcp_server.py`
- Database: Supabase project, tables `services`, `staff`, `working_hours`, `appointments`.
- Working hours: Mon–Sat 10:00 AM–8:00 PM, Sunday 12:00 PM–7:30 PM.
- Reschedule/cancel tools don't exist yet — don't attempt, tell customer to contact salon directly.

## WhatsApp
- Business number: +923423898159
- Owner: +923423898159 (ownerAllowFrom)