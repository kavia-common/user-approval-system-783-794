#!/usr/bin/env python3
"""Initialize and seed SQLite database for main_database.

This script:
- Creates/updates a normalized schema for a social media dashboard:
  users, profiles, posts, engagements, followers, admin_flags, analytics_daily, app_info
- Ensures idempotency (safe to run multiple times)
- Seeds realistic demo data across multiple users, posts, engagements, and analytics
- Maintains compatibility with existing test_db.py (same db filename and connection info)
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_NAME = "myapp.db"
DB_USER = "kaviasqlite"  # Not used for SQLite, but kept for consistency
DB_PASSWORD = "kaviadefaultpassword"  # Not used for SQLite, but kept for consistency
DB_PORT = "5000"  # Not used for SQLite, but kept for consistency

print("Starting SQLite setup...")

# Helper to execute a SQL statement with error handling
def exec_sql(cursor, sql, params=None, ignore_error=False):
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
    except sqlite3.Error as e:
        if ignore_error:
            print(f"Warning (ignored): {e} while executing: {sql}")
        else:
            raise

# Connect (creates db if not exists)
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON")

# Create base info table (kept for compatibility)
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS app_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE NOT NULL,
        value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Users table (retain structure but extend safely)
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        is_active INTEGER DEFAULT 1,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")

# Profiles table
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        full_name TEXT,
        bio TEXT,
        avatar_url TEXT,
        location TEXT,
        website TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id)
    )
""")

# Posts table
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        media_url TEXT,
        is_published INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
""")

# Engagements table
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS engagements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER,                 -- user who engaged (nullable for anonymous)
        type TEXT NOT NULL,              -- like, comment, share, view
        value INTEGER DEFAULT 1,         -- count or weight (e.g., 1 like, 1 view, etc.)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
""")

# Followers table (self-referential relation)
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS followers (
        follower_id INTEGER NOT NULL,
        followee_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (follower_id, followee_id),
        FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (followee_id) REFERENCES users(id) ON DELETE CASCADE,
        CHECK (follower_id <> followee_id)
    )
""")

# Admin flags table for moderation and feature flags per user
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS admin_flags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        flag TEXT NOT NULL,          -- e.g., 'suspended', 'verified', 'beta_tester'
        value INTEGER NOT NULL,      -- 0/1 or small ints
        note TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, flag)
    )
""")

# Analytics daily summary table
exec_sql(cursor, """
    CREATE TABLE IF NOT EXISTS analytics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,                 -- optional user scope (content owner)
        date DATE NOT NULL,
        posts_published INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        shares INTEGER DEFAULT 0,
        views INTEGER DEFAULT 0,
        followers_gained INTEGER DEFAULT 0,
        followers_lost INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, date)
    )
""")

# Useful indices
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON profiles(user_id)")
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id)")
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_engagements_post_id ON engagements(post_id)")
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_engagements_user_id ON engagements(user_id)")
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_engagements_type ON engagements(type)")
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_followers_followee ON followers(followee_id)")
exec_sql(cursor, "CREATE INDEX IF NOT EXISTS idx_analytics_daily_user_date ON analytics_daily(user_id, date)")

# Seed app_info (idempotent)
exec_sql(cursor, "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("project_name", "main_database"))
exec_sql(cursor, "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("version", "1.0.0"))
exec_sql(cursor, "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("author", "Social Dashboard Team"))
exec_sql(cursor, "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)", ("description", "SQLite schema for social media dashboard"))

# Helper: upsert user and return id
def upsert_user(username, email, is_admin=False, is_active=True):
    exec_sql(cursor, "INSERT OR IGNORE INTO users (username, email, is_admin, is_active) VALUES (?, ?, ?, ?)", (username, email, 1 if is_admin else 0, 1 if is_active else 0))
    exec_sql(cursor, "SELECT id FROM users WHERE username=?", (username,))
    row = cursor.fetchone()
    return row[0]

# Helper: upsert profile
def upsert_profile(user_id, full_name, bio, avatar_url=None, location=None, website=None):
    exec_sql(cursor, """
        INSERT INTO profiles (user_id, full_name, bio, avatar_url, location, website, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            full_name=excluded.full_name,
            bio=excluded.bio,
            avatar_url=excluded.avatar_url,
            location=excluded.location,
            website=excluded.website,
            updated_at=CURRENT_TIMESTAMP
    """, (user_id, full_name, bio, avatar_url, location, website))

# Seed users and profiles
users_seed = [
    {"username": "alice", "email": "alice@example.com", "name": "Alice Johnson", "bio": "Coffee lover and tech blogger.", "admin": False, "location": "NY, USA"},
    {"username": "bob", "email": "bob@example.com", "name": "Bob Smith", "bio": "Photographer and traveler.", "admin": False, "location": "LA, USA"},
    {"username": "carol", "email": "carol@example.com", "name": "Carol Chen", "bio": "Product manager. Maker of lists.", "admin": True, "location": "SF, USA"},
    {"username": "dave", "email": "dave@example.com", "name": "Dave Williams", "bio": "Full-stack dev. Open source enthusiast.", "admin": False, "location": "Austin, USA"},
]
user_ids = {}
for u in users_seed:
    uid = upsert_user(u["username"], u["email"], is_admin=u["admin"], is_active=True)
    user_ids[u["username"]] = uid
    upsert_profile(uid, u["name"], u["bio"], avatar_url=f"https://i.pravatar.cc/150?u={u['username']}", location=u["location"], website=f"https://{u['username']}.example.com")

# Seed follower relations (avoid self follow, ensure idempotent via PK)
follows = [
    ("alice", "bob"),
    ("alice", "carol"),
    ("bob", "alice"),
    ("bob", "carol"),
    ("dave", "alice"),
    ("dave", "bob"),
]
for follower, followee in follows:
    exec_sql(cursor, "INSERT OR IGNORE INTO followers (follower_id, followee_id) VALUES (?, ?)", (user_ids[follower], user_ids[followee]))

# Seed admin flags
admin_flags = [
    ("carol", "verified", 1, "Platform admin and verified"),
    ("alice", "beta_tester", 1, "Participates in beta features"),
    ("bob", "suspended", 0, "Not suspended"),
    ("dave", "beta_tester", 1, "Trying experimental dashboard"),
]
for uname, flag, value, note in admin_flags:
    exec_sql(cursor, """
        INSERT INTO admin_flags (user_id, flag, value, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, flag) DO UPDATE SET
            value=excluded.value,
            note=excluded.note
    """, (user_ids[uname], flag, value, note))

# Seed posts for each user
def upsert_post(user_id, content, media_url=None, is_published=True, created_at=None):
    # create a new post always; avoid duplicates by content+user unique? not required; seed modestly
    sql = "INSERT INTO posts (user_id, content, media_url, is_published, created_at) VALUES (?, ?, ?, ?, ?)"
    exec_sql(cursor, sql, (user_id, content, media_url, 1 if is_published else 0, created_at if created_at else datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
    exec_sql(cursor, "SELECT last_insert_rowid()")
    return cursor.fetchone()[0]

random.seed(7)

posts = []
sample_posts = {
    "alice": [
        ("Morning coffee vibes ☕️ #productivity", None),
        ("New blog: SQLite tips and tricks!", None),
        ("Dashboard redesign sneak peek 👀", None),
    ],
    "bob": [
        ("Sunset at the beach 🌅", "https://picsum.photos/seed/beach/600/400"),
        ("Hiking through the mountains 🏔️", "https://picsum.photos/seed/mountain/600/400"),
    ],
    "carol": [
        ("Feature rollout complete. Great job team!", None),
        ("AMA: Product strategy and metrics", None),
    ],
    "dave": [
        ("Open-sourced a new library today!", None),
        ("Refactoring backend services… send coffee.", None),
        ("Live coding stream tonight at 8pm CST.", None),
    ]
}

for uname, items in sample_posts.items():
    for idx, (content, media_url) in enumerate(items):
        # Stagger creation dates over past 10 days
        created_at = (datetime.utcnow() - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23))).strftime("%Y-%m-%d %H:%M:%S")
        pid = upsert_post(user_ids[uname], content, media_url, True, created_at)
        posts.append({"id": pid, "owner": uname})

# Seed engagements: likes, comments, shares, views
engagement_types = ["like", "comment", "share", "view"]
usernames = list(user_ids.keys())

def seed_engagements_for_post(post_id, owner_username):
    # Create a distribution of engagements from other users (and sometimes anonymous for "view")
    n = random.randint(10, 60)
    for _ in range(n):
        etype = random.choices(engagement_types, weights=[3, 1, 1, 8], k=1)[0]
        # 25% chance of anonymous for views only
        engager = None
        if etype == "view" and random.random() < 0.25:
            engager = None
        else:
            # pick a user different from owner
            choices = [u for u in usernames if u != owner_username]
            engager = user_ids[random.choice(choices)] if choices else None
        # Value: views may have value 1, others 1, comments sometimes count 1
        value = 1
        # backdate engagement to the last 10 days
        created_at = (datetime.utcnow() - timedelta(days=random.randint(0, 10), hours=random.randint(0, 23), minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
        exec_sql(cursor, """
            INSERT INTO engagements (post_id, user_id, type, value, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (post_id, engager, etype, value, created_at))

for p in posts:
    seed_engagements_for_post(p["id"], p["owner"])

# Seed analytics_daily summaries for each user over last 14 days
def compute_daily_analytics_for_user(user_id, start_days_ago=14):
    # Initialize map of date -> metrics
    today = datetime.utcnow().date()
    daily = {}
    for delta in range(start_days_ago, -1, -1):
        d = today - timedelta(days=delta)
        daily[d] = {
            "posts_published": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "views": 0,
            "followers_gained": 0,
            "followers_lost": 0,
        }

    # Posts published
    exec_sql(cursor, "SELECT date(created_at), COUNT(*) FROM posts WHERE user_id=? GROUP BY date(created_at)", (user_id,))
    for d, cnt in cursor.fetchall():
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        if dd in daily:
            daily[dd]["posts_published"] = cnt

    # Engagements on user's posts by type
    exec_sql(cursor, """
        SELECT date(e.created_at), e.type, COUNT(*)
        FROM engagements e
        JOIN posts p ON p.id = e.post_id
        WHERE p.user_id=?
        GROUP BY date(e.created_at), e.type
    """, (user_id,))
    for d, etype, cnt in cursor.fetchall():
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        if dd in daily and etype in daily[dd]:
            if etype == "like":
                daily[dd]["likes"] += cnt
            elif etype == "comment":
                daily[dd]["comments"] += cnt
            elif etype == "share":
                daily[dd]["shares"] += cnt
            elif etype == "view":
                daily[dd]["views"] += cnt

    # Followers gained: count new follower relations per day where followee == user
    exec_sql(cursor, "SELECT date(created_at), COUNT(*) FROM followers WHERE followee_id=? GROUP BY date(created_at)", (user_id,))
    for d, cnt in cursor.fetchall():
        dd = datetime.strptime(d, "%Y-%m-%d").date()
        if dd in daily:
            daily[dd]["followers_gained"] += cnt

    # Followers lost (not tracked explicitly; simulate small random churn)
    for dd in daily:
        daily[dd]["followers_lost"] += random.choice([0, 0, 0, 1])  # mostly 0, sometimes 1

    # Upsert into analytics_daily
    for dd, metrics in daily.items():
        exec_sql(cursor, """
            INSERT INTO analytics_daily (
                user_id, date, posts_published, likes, comments, shares, views, followers_gained, followers_lost
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                posts_published=excluded.posts_published,
                likes=excluded.likes,
                comments=excluded.comments,
                shares=excluded.shares,
                views=excluded.views,
                followers_gained=excluded.followers_gained,
                followers_lost=excluded.followers_lost
        """, (user_id, dd.strftime("%Y-%m-%d"),
              metrics["posts_published"], metrics["likes"], metrics["comments"],
              metrics["shares"], metrics["views"], metrics["followers_gained"], metrics["followers_lost"]))

for uname, uid in user_ids.items():
    compute_daily_analytics_for_user(uid, start_days_ago=14)

conn.commit()

# Get database statistics
cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
table_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM app_info")
record_count = cursor.fetchone()[0]

# Close and write connection info
conn.close()

# Save connection information to a file
current_dir = os.getcwd()
connection_string = f"sqlite:///{current_dir}/{DB_NAME}"

try:
    with open("db_connection.txt", "w") as f:
        f.write(f"# SQLite connection methods:\n")
        f.write(f"# Python: sqlite3.connect('{DB_NAME}')\n")
        f.write(f"# Connection string: {connection_string}\n")
        f.write(f"# File path: {current_dir}/{DB_NAME}\n")
    print("Connection information saved to db_connection.txt")
except Exception as e:
    print(f"Warning: Could not save connection info: {e}")

# Create environment variables file for Node.js viewer
db_path = os.path.abspath(DB_NAME)

# Ensure db_visualizer directory exists
if not os.path.exists("db_visualizer"):
    os.makedirs("db_visualizer", exist_ok=True)
    print("Created db_visualizer directory")

try:
    with open("db_visualizer/sqlite.env", "w") as f:
        f.write(f"export SQLITE_DB=\"{db_path}\"\n")
    print(f"Environment variables saved to db_visualizer/sqlite.env")
except Exception as e:
    print(f"Warning: Could not save environment variables: {e}")

print("\nSQLite setup complete!")
print(f"Database: {DB_NAME}")
print(f"Location: {current_dir}/{DB_NAME}")
print("")
print("To use with Node.js viewer, run: source db_visualizer/sqlite.env")
print("\nTo connect to the database, use one of the following methods:")
print(f"1. Python: sqlite3.connect('{DB_NAME}')")
print(f"2. Connection string: {connection_string}")
print(f"3. Direct file access: {current_dir}/{DB_NAME}")
print("")
print("Database statistics:")
print(f"  Tables: {table_count}")
print(f"  App info records: {record_count}")

# If sqlite3 CLI is available, show how to use it
try:
    import subprocess
    result = subprocess.run(['which', 'sqlite3'], capture_output=True, text=True)
    if result.returncode == 0:
        print("")
        print("SQLite CLI is available. You can also use:")
        print(f"  sqlite3 {DB_NAME}")
except:
    pass

print("\nScript completed successfully.")
