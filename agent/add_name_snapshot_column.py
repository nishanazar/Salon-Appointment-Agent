"""One-time migration: add customer_name_snapshot column to appointments
and backfill existing rows with the current customers.name.

The direct db.<ref>.supabase.co host is IPv6-only and this network has no
IPv6, so we connect through Supabase's IPv4 session pooler instead. The
correct pooler region is auto-discovered by trying known regions.

Safe & idempotent:
  - ALTER TABLE ... ADD COLUMN IF NOT EXISTS
  - UPDATE only rows where snapshot IS NULL
"""

import os
import psycopg2
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    exit(1)

parsed = urlparse(DATABASE_URL)
PASSWORD = parsed.password
DB_NAME = parsed.path.lstrip("/") or "postgres"

# Username is "postgres.<PROJECT_REF>" — extract the ref
_pooler_user = parsed.username or ""
if "." in _pooler_user:
    PROJECT_REF = _pooler_user.split(".", 1)[1]
else:
    # Fallback: old-style direct host db.<ref>.supabase.co
    PROJECT_REF = (parsed.hostname or "").split(".")[1]

# If already a pooler URL, just connect directly — no discovery needed
_pooler_host = parsed.hostname or ""
if "pooler.supabase.com" in _pooler_host:
    try:
        conn = psycopg2.connect(
            host=_pooler_host,
            port=parsed.port or 5432,
            user=_pooler_user,
            password=PASSWORD,
            dbname=DB_NAME,
            connect_timeout=8,
        )
        print(f"Connected via pooler: {_pooler_host}")
    except psycopg2.OperationalError as e:
        print(f"ERROR: pooler connection failed: {e}")
        conn = None
else:
    # Supabase session-pooler regions (project ref goes in the username)
    CANDIDATES = [
        "aws-0-ap-south-1",       # Mumbai
        "aws-0-ap-southeast-1",   # Singapore
        "aws-0-ap-northeast-1",   # Tokyo
        "aws-0-eu-west-1",        # Ireland
        "aws-0-us-east-1",        # N. Virginia
    ]
    for region in CANDIDATES:
        host = f"{region}.pooler.supabase.com"
        try:
            conn = psycopg2.connect(
                host=host,
                port=5432,
                user=f"postgres.{PROJECT_REF}",
                password=PASSWORD,
                dbname=DB_NAME,
                connect_timeout=8,
            )
            print(f"Connected via session pooler: {host}")
            break
        except psycopg2.OperationalError as e:
            msg = str(e).strip().splitlines()[0]
            print(f"  {region}: {msg}")
            conn = None

if conn is None:
    print("\nERROR: could not connect to Supabase.")
    print("Run this in Supabase Dashboard > SQL Editor instead:")
    print("  ALTER TABLE appointments ADD COLUMN IF NOT EXISTS customer_name_snapshot TEXT;")
    print("  UPDATE appointments a SET customer_name_snapshot = c.name")
    print("    FROM customers c WHERE a.customer_id = c.id AND a.customer_name_snapshot IS NULL;")
    exit(1)

conn.autocommit = True
cur = conn.cursor()

# Step 1: Add the column (idempotent)
cur.execute(
    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS customer_name_snapshot TEXT"
)
print("ALTER TABLE executed — customer_name_snapshot column added.")

# Step 2: Backfill existing rows with the current customers.name
cur.execute(
    """
    UPDATE appointments a
    SET customer_name_snapshot = c.name
    FROM customers c
    WHERE a.customer_id = c.id
      AND a.customer_name_snapshot IS NULL
    """
)
backfilled = cur.rowcount
print(f"Backfilled {backfilled} existing appointment(s) with current customer name.")

# Step 3: Verify
cur.execute(
    """
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_name = 'appointments'
    ORDER BY ordinal_position;
    """
)
print("\n=== appointments columns ===")
for name, dtype, default in cur.fetchall():
    print(f"  {name:30s} {dtype:15s} {default or ''}")

cur.close()
conn.close()
print("\nMigration done.")
