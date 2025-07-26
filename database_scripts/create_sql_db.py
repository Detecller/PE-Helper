import sqlite3

conn = sqlite3.connect('../databases/pe_helper.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    discord_id VARCHAR(32) PRIMARY KEY,
    admin_number VARCHAR(7) UNIQUE,
    name VARCHAR(100),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expiry TIMESTAMP
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS all_bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    room VARCHAR(50) NOT NULL,
    time_slot VARCHAR(50) NOT NULL,
    admin_num VARCHAR(7),
    AY VARCHAR(4) NOT NULL
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS member_piano_groups (
    member_piano_groups_id INTEGER PRIMARY KEY AUTOINCREMENT,
    Advanced INTEGER NOT NULL,
    Intermediate INTEGER NOT NULL,
    Novice INTEGER NOT NULL,
    Foundational INTEGER NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS summary_numbers (
    summary_numbers_id INTEGER PRIMARY KEY AUTOINCREMENT,
    AY VARCHAR(4) NOT NULL,
    members_num INTEGER NOT NULL,
    alumni_num INTEGER NOT NULL,
    new_members_num INTEGER NOT NULL
);
''')