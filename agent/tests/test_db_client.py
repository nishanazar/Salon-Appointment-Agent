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
    get_or_create_customer,
    get_services,
    reschedule_appointment,
    sb,
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


# ── get_or_create_customer tests ─────────────────────────────────────────────

def test_create_new_customer(register_phone):
    """A brand-new phone+name must insert a row and return its id."""
    phone = "9990000010"
    register_phone(phone)

    cid = get_or_create_customer(phone, "Ali Khan")
    assert isinstance(cid, int), f"Expected int id, got {type(cid)}"

    # Verify the row actually exists with correct data
    row = sb.table("customers").select("id, name, phone").eq("phone", phone).execute().data
    assert len(row) == 1
    assert row[0]["name"] == "Ali Khan"
    assert row[0]["id"] == cid


def test_existing_customer_same_name_no_update(register_phone):
    """If the customer exists and the same name is passed, no update
    should happen — just return the existing id."""
    phone = "9990000011"
    register_phone(phone)

    cid1 = get_or_create_customer(phone, "Sara Ahmed")
    cid2 = get_or_create_customer(phone, "Sara Ahmed")

    assert cid1 == cid2, "Same phone must return the same customer id"

    row = sb.table("customers").select("name").eq("phone", phone).execute().data[0]
    assert row["name"] == "Sara Ahmed"


def test_existing_customer_different_name_updates(register_phone):
    """If the customer exists and a DIFFERENT name is passed, the name
    must be updated to the latest value."""
    phone = "9990000012"
    register_phone(phone)

    cid1 = get_or_create_customer(phone, "Fatima Old")
    cid2 = get_or_create_customer(phone, "Fatima New")

    assert cid1 == cid2, "Same phone must return the same customer id"

    row = sb.table("customers").select("name").eq("phone", phone).execute().data[0]
    assert row["name"] == "Fatima New", (
        f"Expected name to be updated to 'Fatima New', got {row['name']!r}"
    )


def test_existing_customer_none_name_keeps_old(register_phone):
    """If name=None is passed for an existing customer, the old name
    must remain unchanged."""
    phone = "9990000013"
    register_phone(phone)

    cid1 = get_or_create_customer(phone, "Hassan Original")
    cid2 = get_or_create_customer(phone, None)  # no name provided

    assert cid1 == cid2

    row = sb.table("customers").select("name").eq("phone", phone).execute().data[0]
    assert row["name"] == "Hassan Original", (
        f"Name should remain 'Hassan Original' when None passed, got {row['name']!r}"
    )


def test_existing_customer_empty_name_keeps_old(register_phone):
    """If an empty-string name is passed for an existing customer, the
    old name must remain unchanged."""
    phone = "9990000014"
    register_phone(phone)

    cid1 = get_or_create_customer(phone, "Zainab Keep")
    cid2 = get_or_create_customer(phone, "")  # empty string

    assert cid1 == cid2

    row = sb.table("customers").select("name").eq("phone", phone).execute().data[0]
    assert row["name"] == "Zainab Keep", (
        f"Name should remain 'Zainab Keep' when empty string passed, got {row['name']!r}"
    )


def test_new_customer_no_name_raises():
    """Creating a customer without a name (None) must raise ValueError."""
    with pytest.raises(ValueError, match="name is required"):
        get_or_create_customer("9990000099", None)


def test_book_appointment_updates_customer_name(register_phone):
    """End-to-end: booking with a changed name must update the
    customer record via get_or_create_customer."""
    service = _get_test_service()
    phone = "9990000015"
    register_phone(phone)

    date_str = _future_date()

    # First booking with old name
    book_appointment(phone, "Old Name", service["id"], f"{date_str} 11:00")

    # Second booking with new name (different time to avoid conflict)
    book_appointment(phone, "New Name", service["id"], f"{date_str} 14:00")

    row = sb.table("customers").select("name").eq("phone", phone).execute().data[0]
    assert row["name"] == "New Name", (
        f"book_appointment should update customer name, got {row['name']!r}"
    )


def test_appointment_name_snapshot_preserved(register_phone):
    """Each appointment must freeze the customer name at booking time.
    Even if the customer's name changes later, old appointments must
    still show the original snapshot."""
    service = _get_test_service()
    phone = "9990000016"
    register_phone(phone)

    date_str = _future_date()

    # First booking with original name
    appt1 = book_appointment(phone, "Original Name", service["id"], f"{date_str} 11:00")

    # Second booking updates the customer name to a new value
    appt2 = book_appointment(phone, "Updated Name", service["id"], f"{date_str} 14:00")

    # Verify: appt1 should still have "Original Name" as snapshot
    row1 = sb.table("appointments").select("customer_name_snapshot") \
        .eq("id", appt1["id"]).execute().data[0]
    assert row1["customer_name_snapshot"] == "Original Name", (
        f"First appointment snapshot should be 'Original Name', "
        f"got {row1['customer_name_snapshot']!r}"
    )

    # Verify: appt2 should have "Updated Name" as snapshot
    row2 = sb.table("appointments").select("customer_name_snapshot") \
        .eq("id", appt2["id"]).execute().data[0]
    assert row2["customer_name_snapshot"] == "Updated Name", (
        f"Second appointment snapshot should be 'Updated Name', "
        f"got {row2['customer_name_snapshot']!r}"
    )

    # Verify: get_customer_appointments returns the snapshot, not the live name
    appts = get_customer_appointments(phone)
    appt1_data = next(a for a in appts if a["id"] == appt1["id"])
    appt2_data = next(a for a in appts if a["id"] == appt2["id"])
    assert appt1_data["customer_name"] == "Original Name", (
        f"get_customer_appointments should return snapshot, got {appt1_data['customer_name']!r}"
    )
    assert appt2_data["customer_name"] == "Updated Name"
