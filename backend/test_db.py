import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

cursor = conn.cursor()
cursor.execute("SELECT id, name FROM intersections;")
rows = cursor.fetchall()

for row in rows:
    print(f"{row[0]} — {row[1]}")

conn.close()
print("\nDatabase connection successful.")