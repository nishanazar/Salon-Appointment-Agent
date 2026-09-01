"""
Integration tests for db_client.py — runs against the LIVE Supabase
database (no mocks). Every test uses fake phone numbers (999000000X
series) and the conftest.py autouse fixture automatically cleans up
all test data after each test.

Run command:
    pytest tests/ -v
"""

from datetime import datetime, timedelta

import pytest

from db_client import (
    book_appointment,
    cancel_appointment,
    get_customer_appointments,
    get_services,
    reschedule_appointment,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _get_test_service():
    """Return a real active service from the database for testing."""
    services = get_services()
    assert len(services) > 0, (
        "No active services in database — cannot run test. "
        "Please add at least one service with active=true."
    )
    return services[0]


def _future_date() -> str:
    """A date ~7 days from now, guaranteed to be in the future and
    within normal working hours."""
    return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")


# ── tests ─────────────────────────────────────────────────────────────────────

def test_get_services_returns_list():
    """Confirm get_services() returns a non-empty list where every
    service has 'name' and 'price' keys."""
    services = get_services()

    assert isinstance(services, list), "get_services() must return a list"
    assert len(services) > 0, "Expected at least one active service in the database"

    for svc in services:
        assert "name" in svc, f"Service missing 'name' key: {svc}"
        assert "price" in svc, f"Service missing 'price' key: {svc}"


def test_double_booking_prevented(register_phone):
    """Booking the exact same slot twice for the same staff must fail
    with an exception (database exclusion constraint)."""
    service = _get_test_service()
    phone = "9990000001"
    name = "Test Double-Book"
    register_phone(phone)

    date_str = _future_date()
    start_time = f"{date_str} 11:00"

    # First booking — should succeed
    first = book_appointment(phone, name, service["id"], start_time)
    assert first is not None, "First booking should succeed"

    # Second booking on the same slot — must raise
    with pytest.raises(Exception) as exc_info:
        book_appointment(phone, name, service["id"], start_time)

    # Verify something about the error (flexible: exclusion constraint message varies)
    error_msg = str(exc_info.value).lower()
    assert any(
        token in error_msg
        for token in ("conflict", "duplicate", "exclusion", "not available", "already")
    ) or "23P01" in str(exc_info.value), (
        f"Expected a booking-conflict error, got: {exc_info.value}"
    )


def test_cancel_only_own_booking(register_phone):
    """Customer B must NOT be able to cancel Customer A's appointment.
    The function raises ValueError('Appointment not found')."""
    service = _get_test_service()
    phone_a = "9990000002"
    phone_b = "9990000003"
    register_phone(phone_a)
    register_phone(phone_b)

    date_str = _future_date()

    # Customer A books an appointment
    appt_a = book_appointment(phone_a, "Test Customer A", service["id"], f"{date_str} 12:00")

    # Customer B also needs to exist (book something at a different time
    # so the phone is registered in the customers table)
    book_appointment(phone_b, "Test Customer B", service["id"], f"{date_str} 16:00")

    # Customer B tries to cancel Customer A's appointment — must fail
    with pytest.raises(ValueError, match="not found"):
        cancel_appointment(phone_b, str(appt_a["id"]))

    # Verify Customer A's booking is still confirmed
    appts = get_customer_appointments(phone_a)
    assert any(a["id"] == appt_a["id"] for a in appts), (
        "Customer A's booking should still be confirmed after B's failed cancel attempt"
    )


def test_reschedule_conflict_detected(register_phone):
    """Rescheduling appointment A into appointment B's time slot (same
    staff) must raise ValueError('not available')."""
    service = _get_test_service()
    phone = "9990000004"
    name = "Test Reschedule"
    register_phone(phone)

    date_str = _future_date()

    # Book appointment 1 at 13:00
    appt1 = book_appointment(phone, name, service["id"], f"{date_str} 13:00")

    # Book appointment 2 at 15:00 (same staff — default first active staff)
    appt2 = book_appointment(phone, name, service["id"], f"{date_str} 15:00")

    # Try to reschedule appt1 to appt2's slot (15:00) — must fail
    new_start = datetime.strptime(f"{date_str} 15:00", "%Y-%m-%d %H:%M")
    with pytest.raises(ValueError, match="not available"):
        reschedule_appointment(phone, str(appt1["id"]), new_start)

    # Verify appt1 is still at 13:00 (unchanged)
    appts = get_customer_appointments(phone)
    appt1_data = next((a for a in appts if a["id"] == appt1["id"]), None)
    assert appt1_data is not None, "Appointment 1 should still exist"
    assert "13:00" in appt1_data["start_time"], (
        f"Appointment 1 should still be at 13:00, got: {appt1_data['start_time']}"
    )


def test_phone_customer_lookup(register_phone):
    """get_customer_appointments() must find a booking by the phone
    number it was created with."""
    service = _get_test_service()
    phone = "9990000005"
    name = "Test Lookup"
    register_phone(phone)

    date_str = _future_date()

    appt = book_appointment(phone, name, service["id"], f"{date_str} 10:00")

    # Look up by the same phone — should find the booking
    appts = get_customer_appointments(phone)
    assert len(appts) > 0, "Expected at least one appointment for this phone"
    assert any(a["id"] == appt["id"] for a in appts), (
        f"Booking #{appt['id']} not found via phone lookup"
    )

    # Look up by a non-existent phone — should return empty
    bogus_appts = get_customer_appointments("9990000099")
    assert bogus_appts == [], (
        f"Expected no appointments for unknown phone, got: {bogus_appts}"
    )
