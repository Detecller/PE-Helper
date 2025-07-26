import sqlite3

conn = sqlite3.connect('../databases/pe_helper.db')
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS users;")

cursor.execute("DROP TABLE IF EXISTS all_bookings;")
cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'all_bookings';")

cursor.execute("DROP TABLE IF EXISTS member_piano_groups;")
cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'member_piano_groups';")

cursor.execute("DROP TABLE IF EXISTS summary_numbers;")
cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'summary_numbers';")

conn.commit()

conn.close()