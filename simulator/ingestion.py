import json

import paho.mqtt.client as mqtt
import psycopg2


BROKER = "localhost"
PORT = 1883

MQTT_TOPIC = "traffic/readings/#"


DB_CONFIG = {
    "host": "localhost",
    "database": "traffic_db",
    "user": "postgres",
    "password": "admin123",
    "port": 5432
}


conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("Connected to PostgreSQL.")


def prepare_database():
    try:
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'traffic_data'
        """)

        columns = {row[0] for row in cursor.fetchall()}

        if "avg_speed_kmph" in columns and "avg_speed_kmh" not in columns:
            cursor.execute("""
                ALTER TABLE traffic_data
                RENAME COLUMN avg_speed_kmph TO avg_speed_kmh
            """)
            print("Renamed avg_speed_kmph to avg_speed_kmh.")

        if "direction" not in columns:
            cursor.execute("""
                ALTER TABLE traffic_data
                ADD COLUMN direction VARCHAR(3)
            """)
            print("Added direction column.")

        conn.commit()

    except Exception as e:
        conn.rollback()
        print("Database preparation error:", e)
        raise


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to: {MQTT_TOPIC}")
    else:
        print("MQTT connection failed with code:", rc)


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))

        print(f"\nReceived from {msg.topic}:")
        print(data)

        required_fields = [
            "intersection_id",
            "timestamp",
            "vehicle_count",
            "avg_speed_kmh",
            "direction"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing field: {field}")

        if data["intersection_id"] not in [
            "IN_001",
            "IN_002",
            "IN_003",
            "IN_004",
            "IN_005",
            "IN_006",
            "IN_007",
            "IN_008"
        ]:
            raise ValueError("Invalid intersection_id")

        if data["direction"] not in ["N-S", "E-W"]:
            raise ValueError("Invalid direction")

        if not isinstance(data["vehicle_count"], int):
            raise ValueError("vehicle_count must be a whole number")

        if data["vehicle_count"] < 0:
            raise ValueError("vehicle_count cannot be negative")

        if not 0 <= float(data["avg_speed_kmh"]) <= 120:
            raise ValueError("avg_speed_kmh must be between 0 and 120")

        cursor.execute(
            """
            INSERT INTO traffic_data
            (
                intersection_id,
                timestamp,
                vehicle_count,
                avg_speed_kmh,
                direction
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                data["intersection_id"],
                data["timestamp"],
                data["vehicle_count"],
                data["avg_speed_kmh"],
                data["direction"]
            )
        )

        conn.commit()

        print("Inserted into PostgreSQL successfully.")

    except Exception as e:
        conn.rollback()
        print("Error processing message:", e)


prepare_database()

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message

print("Connecting to MQTT broker...")

client.connect(BROKER, PORT, 60)

print("Listening for traffic messages...")
print("Press Ctrl+C to stop.")

try:
    client.loop_forever()

except KeyboardInterrupt:
    print("\nIngestion stopped.")

finally:
    cursor.close()
    conn.close()