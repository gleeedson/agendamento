import sqlite3

conn = sqlite3.connect('database.db')
conn.execute("UPDATE alembic_version SET version_num='13765f1c46ca'")
conn.commit()
conn.close()
