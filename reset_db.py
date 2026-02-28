#!/usr/bin/env python3
"""
reset_db.py — Delete ALL race data from the Pinewood Derby Supabase database,
              including all car photos in the storage bucket.

Usage:
    python3 reset_db.py

Requires: requests  (pip install requests)
"""

import sys
import requests

# ── Credentials (same as config.js) ──────────────────────────────────────────
SUPABASE_URL = "https://fixnbthycrvegkofvzfv.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZpeG5idGh5Y3J2ZWdrb2Z2emZ2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIyOTQwMDcsImV4cCI6MjA4Nzg3MDAwN30."
    "4N67KwFK6WZwljLT7jQg_ubZJzEu5HgPd1X4DGDGEiY"
)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}


def delete_bucket_files(bucket: str = "car-images") -> None:
    """Delete every file in a Supabase Storage bucket."""
    list_url = f"{SUPABASE_URL}/storage/v1/object/list/{bucket}"
    r = requests.post(list_url, headers=HEADERS, json={"prefix": "", "limit": 1000, "offset": 0})
    if r.status_code not in (200, 204):
        print(f"  ERROR listing {bucket}: {r.status_code} — {r.text}")
        return

    files = r.json()
    if not files:
        print(f"  ✓ {bucket} (already empty)")
        return

    names = [f["name"] for f in files if isinstance(f, dict) and "name" in f]
    if not names:
        print(f"  ✓ {bucket} (already empty)")
        return

    del_url = f"{SUPABASE_URL}/storage/v1/object/{bucket}"
    r2 = requests.delete(del_url, headers=HEADERS, json={"prefixes": names})
    if r2.status_code not in (200, 204):
        print(f"  ERROR deleting files in {bucket}: {r2.status_code} — {r2.text}")
        return

    print(f"  ✓ {bucket} ({len(names)} photo(s) deleted)")


def delete_all(table: str) -> None:
    """Delete every row in a table using the Supabase REST API."""
    # UUID PKs: gte the nil UUID matches every row
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=gte.00000000-0000-0000-0000-000000000000"
    r = requests.delete(url, headers=HEADERS)
    if r.status_code not in (200, 204):
        print(f"  ERROR deleting {table}: {r.status_code} — {r.text}")
        sys.exit(1)
    print(f"  ✓ {table}")


def reset_race_state() -> None:
    """Reset the race_state singleton row back to all-nulls."""
    url = f"{SUPABASE_URL}/rest/v1/race_state?id=eq.1"
    payload = {
        "current_round_id": None,
        "current_heat_id":  None,
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    if r.status_code not in (200, 204):
        print(f"  ERROR resetting race_state: {r.status_code} — {r.text}")
        sys.exit(1)
    print(f"  ✓ race_state (reset to nulls)")


def main() -> None:
    print("\n⚠️  This will permanently delete ALL race data.")
    confirm = input("Type  YES  to continue: ").strip()
    if confirm != "YES":
        print("Aborted.")
        sys.exit(0)

    print("\nDeleting data (order respects foreign keys)…")

    # Null out race_state FK references first so heats/rounds can be deleted
    reset_race_state()
    delete_all("heat_results")
    delete_all("heat_entries")
    delete_all("heats")
    delete_all("rounds")
    delete_all("cars")
    delete_bucket_files("car-images")

    print("\n✅  Database cleared successfully.\n")


if __name__ == "__main__":
    main()
