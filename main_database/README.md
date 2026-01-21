# Main Database (SQLite)

Initializes and seeds the SQLite database used by the backend.

## Files
- myapp.db: SQLite database file (created by init_db.py)
- init_db.py: Creates schema and seeds data
- migrate_and_seed.py: Runs init and prints table counts
- db_connection.txt: Connection info and absolute path
- db_visualizer/: Simple Node viewer (optional)

## Usage

1) Initialize/seed:
   python3 migrate_and_seed.py
   # or
   python3 init_db.py

2) Locate database path:
   See db_connection.txt. Example path:
   /tmp/kavia/workspace/code-generation/user-approval-system-783-794/main_database/myapp.db

3) Point backend DB_PATH to the absolute path from step 2.

## Notes
- Schema includes users, profiles, posts, engagements, followers, admin_flags, analytics_daily, app_info.
- Idempotent: safe to run init multiple times.
