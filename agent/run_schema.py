"""
run_schema.py
Connects to Supabase Postgres via DATABASE_URL, runs schema.sql,
and prints the tables that were created.

Usage:  python run_schema.py
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env — get it from Supabase Dashboard > Settings > Database > Connection string > Session mode")
    exit(1)

# ── Read schema.sql ──────────────────────────────────────────────────────────
schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
with open(schema_path, "r", encoding="utf-8") as f:
    schema_sql = f.read()

# ── Execute schema ────────────────────────────────────────────────────────────
print("Connecting to Supabase Postgres...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

print("Running schema.sql...")
cur.execute(schema_sql)
print("schema.sql executed successfully.\n")

# ── List all user tables ──────────────────────────────────────────────────────
cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name;
""")

tables = [row[0] for row in cur.fetchall()]
print("=== Tables in public schema ===")
for t in tables:
    print(f"  - {t}")

# ── Quick row-count check ─────────────────────────────────────────────────────
print("\n=== Row counts ===")
for table in ["services", "staff", "working_hours"]:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"  {table}: {count} rows")

cur.close()
conn.close()
print("\nDone! Your salon DB is ready.")
