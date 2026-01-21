#!/usr/bin/env python3
"""Helper to run init_db.py and then verify core tables exist and show brief counts."""

import os
import sqlite3
import subprocess
import sys

DB_NAME = "myapp.db"

def main():
    # Run init script to ensure schema and seeds
    print("Running init_db.py ...")
    res = subprocess.run([sys.executable, "init_db.py"])
    if res.returncode != 0:
        print("init_db.py failed")
        sys.exit(1)

    if not os.path.exists(DB_NAME):
        print(f"Database {DB_NAME} not found after init.")
        sys.exit(1)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")

    tables = ["users", "profiles", "posts", "engagements", "followers", "admin_flags", "analytics_daily", "app_info"]
    print("\nTable counts:")
    for t in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            c = cur.fetchone()[0]
            print(f"  {t}: {c}")
        except Exception as e:
            print(f"  {t}: error - {e}")

    conn.close()
    print("\nMigration and seed verification complete.")

if __name__ == "__main__":
    main()
