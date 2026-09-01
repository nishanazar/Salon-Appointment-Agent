"""
update_data.py
Updates working_hours and services tables in Supabase.

- working_hours: clears all rows, inserts 7 new rows (0=Mon ... 6=Sun)
- services: adds 20 new services (skips duplicates by name)
"""

from db_client import sb

# ═══════════════════════════════════════════════════════════════════
# 1. WORKING HOURS — clear & re-insert
#    day_of_week: 0=Monday, 1=Tuesday, ... 5=Saturday, 6=Sunday
# ═══════════════════════════════════════════════════════════════════

print("=== Updating working_hours ===")

# Clear existing rows
sb.table("working_hours").delete().neq("id", 0).execute()
print("  Cleared old working_hours rows.")

new_hours = [
    {"day_of_week": 0, "start_time": "10:00", "end_time": "20:00"},   # Monday
    {"day_of_week": 1, "start_time": "10:00", "end_time": "20:00"},   # Tuesday
    {"day_of_week": 2, "start_time": "10:00", "end_time": "20:00"},   # Wednesday
    {"day_of_week": 3, "start_time": "10:00", "end_time": "20:00"},   # Thursday
    {"day_of_week": 4, "start_time": "10:00", "end_time": "20:00"},   # Friday
    {"day_of_week": 5, "start_time": "10:00", "end_time": "20:00"},   # Saturday
    {"day_of_week": 6, "start_time": "12:00", "end_time": "19:30"},   # Sunday
]

sb.table("working_hours").insert(new_hours).execute()
print(f"  Inserted {len(new_hours)} new working_hours rows.")

# ═══════════════════════════════════════════════════════════════════
# 2. SERVICES — add 20 new services (skip if name already exists)
# ═══════════════════════════════════════════════════════════════════

print("\n=== Updating services ===")

new_services = [
    {"name": "Female Cut & Finish",               "duration_minutes": 60,  "price": 8250},
    {"name": "Bangs Trimming",                    "duration_minutes": 15,  "price": 2500},
    {"name": "Female Child Cut",                  "duration_minutes": 30,  "price": 4000},
    {"name": "Female Hair Styling & Trimming",    "duration_minutes": 45,  "price": 5000},
    {"name": "Hair Up",                           "duration_minutes": 45,  "price": 3500},
    {"name": "Blow Dry",                          "duration_minutes": 30,  "price": 3000},
    {"name": "Full Head Highlights",              "duration_minutes": 180, "price": 40000},
    {"name": "Half Head Highlights",              "duration_minutes": 150, "price": 32000},
    {"name": "T-Section Highlights",              "duration_minutes": 120, "price": 22000},
    {"name": "Glossing",                          "duration_minutes": 90,  "price": 30000},
    {"name": "Balayage",                          "duration_minutes": 180, "price": 40000},
    {"name": "Roots Regrowth 2-4 inches",         "duration_minutes": 60,  "price": 8500},
    {"name": "Roots Regrowth 5-8 inches",         "duration_minutes": 90,  "price": 10000},
    {"name": "Waving/Perming",                    "duration_minutes": 150, "price": 23000},
    {"name": "Smoothing Treatment",               "duration_minutes": 120, "price": 17000},
    {"name": "Complete Smoothing",                "duration_minutes": 180, "price": 30000},
    {"name": "Post Wash",                         "duration_minutes": 20,  "price": 3500},
    {"name": "Guinot Detoxygene Facial",          "duration_minutes": 60,  "price": 11000},
    {"name": "Hydra Facial",                      "duration_minutes": 60,  "price": 14000},
    {"name": "Eye Brow Tint & Clean",             "duration_minutes": 20,  "price": 1800},
]

# Get existing service names
existing = sb.table("services").select("name").execute().data or []
existing_names = {s["name"].lower() for s in existing}

added = 0
skipped = 0

for svc in new_services:
    if svc["name"].lower() in existing_names:
        print(f"  [SKIP] {svc['name']} (already exists)")
        skipped += 1
    else:
        svc["active"] = True
        sb.table("services").insert(svc).execute()
        print(f"  [ADD]  {svc['name']} — {svc['duration_minutes']}min — Rs.{svc['price']}")
        added += 1

print(f"\n  Added: {added}, Skipped: {skipped}")

# ═══════════════════════════════════════════════════════════════════
# 3. PRINT FINAL DATA
# ═══════════════════════════════════════════════════════════════════

day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

print("\n" + "=" * 60)
print("FINAL: working_hours")
print("=" * 60)
hours = sb.table("working_hours").select("*").order("day_of_week").execute().data or []
for h in hours:
    d = h["day_of_week"]
    name = day_names[d] if d < 7 else f"Day {d}"
    print(f"  {name:<12} ({d})  {h['start_time'][:5]} - {h['end_time'][:5]}")

print("\n" + "=" * 60)
print("FINAL: services")
print("=" * 60)
services = sb.table("services").select("*").eq("active", True).order("id").execute().data or []
for s in services:
    print(f"  [{s['id']:>2}] {s['name']:<42} {s['duration_minutes']:>3}min  Rs.{s['price']:>8}")

print(f"\nTotal services: {len(services)}")
print("Done!")
