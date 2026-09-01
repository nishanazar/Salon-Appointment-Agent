"""One-time migration: add reminder_sent column to appointments.

The direct db.<ref>.supabase.co host is IPv6-only and this network has no
IPv6, so we connect through Supabase's IPv4 session pooler instead. The
correct pooler region is auto-discovered by trying known regions.

Safe & idempotent: ALTER TABLE ... ADD COLUMN IF NOT EXISTS.
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
PROJECT_REF = (parsed.hostname or "").split(".")[1]  # db.<ref>.supabase.co
PASSWORD = parsed.password
DB_NAME = parsed.path.lstrip("/") or "postgres"

# Supabase session-pooler regions (project ref goes in the username)
CANDIDATES = [
    "aws-0-ap-south-1",       # Mumbai (closest to Pakistan)
    "aws-0-ap-southeast-1",   # Singapore
    "aws-0-ap-southeast-2",   # Sydney
    "aws-0-ap-northeast-1",   # Tokyo
    "aws-0-ap-northeast-2",   # Seoul
    "aws-0-eu-central-1",     # Frankfurt
    "aws-0-eu-west-1",        # Ireland
    "aws-0-eu-west-2",        # London
    "aws-0-eu-west-3",        # Paris
    "aws-0-eu-north-1",       # Stockholm
    "aws-0-eu-south-1",       # Milan
    "aws-0-us-east-1",        # N. Virginia
    "aws-0-us-west-1",        # N. California
    "aws-0-us-west-2",        # Oregon
    "aws-0-ca-central-1",     # Canada
    "aws-0-sa-east-1",        # Sao Paulo
]

conn = None
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
    print("\nERROR: could not reach any Supabase pooler region.")
    print("Run this in Supabase Dashboard > SQL Editor instead:")
    print("  ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE;")
    exit(1)

conn.autocommit = True
cur = conn.cursor()

cur.execute(
    "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE"
)
print("\nALTER TABLE executed.")

cur.execute(
    """
    SELECT column_name, data_type, column_default
    FROM information_schema.columns
    WHERE table_name = 'appointments'
    ORDER BY ordinal_position;
    """
)
print("=== appointments columns ===")
for name, dtype, default in cur.fetchall():
    print(f"  {name:15s} {dtype:10s} {default or ''}")

cur.close()
conn.close()
print("\nMigration done.")
