# user-approval-system-783-794 (main_database)

SQLite database for the Social Dashboard.

## Quickstart

1) Initialize:
   cd main_database
   python3 migrate_and_seed.py

2) Find DB path:
   - Open main_database/db_connection.txt
   - Copy the absolute path to myapp.db

3) Backend configuration:
   - Set api_backend/.env DB_PATH to the absolute path from step 2

Optional: Start the simple DB viewer
   cd main_database/db_visualizer
   source ../sqlite.env
   npm install
   npm start
