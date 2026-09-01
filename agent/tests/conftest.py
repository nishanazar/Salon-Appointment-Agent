"""
Pytest configuration for salon booking system integration tests.

Tests run against the LIVE Supabase database (no mocks). A per-test
cleanup fixture automatically removes all test data (appointments +
customers) identified by the fake phone numbers registered during
each test.
"""

import pytest
from db_client import sb  # same Supabase client the app uses

# Prefix all test phones with this so they are instantly identifiable
# and never collide with real customer data.
TEST_PHONE_PREFIX = "999000000"


@pytest.fixture(autouse=False)
def register_phone():
    """Register test phones during the test; delete all associated
    appointments + customers after the test finishes (pass or fail)."""
    phones_to_clean: list[str] = []

    def register_phone(phone: str) -> None:
        if phone not in phones_to_clean:
            phones_to_clean.append(phone)

    yield register_phone

    # ── teardown: always runs, even on test failure ──────────────────────────
    for phone in phones_to_clean:
        rows = sb.table("customers").select("id").eq("phone", phone).execute().data
        for customer in rows:
            # Delete every appointment for this test customer (any status)
            sb.table("appointments").delete().eq("customer_id", customer["id"]).execute()
            sb.table("customers").delete().eq("id", customer["id"]).execute()
