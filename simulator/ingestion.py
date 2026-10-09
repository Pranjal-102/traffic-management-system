
import json
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg2

BROKER = "localhost"
PORT = 1883
TOPIC = "traffic/readings/+"

DB_CONFIG = {
    "host": "localhost",
    "database": "traffic_db",
    "user": "postgres",
    "password": os.getenv("TRAFFIC_DB_PASSWORD", ""),
    "port": 5432
}

conn = None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
        client.subscribe(TOPIC)
        print(f"Subscribed to {TOPIC}")
    else:
        print(f"MQTT connection failed: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))

        intersection_id = data["intersection_id"]
        timestamp_text = data["timestamp"]
        timestamp = datetime.fromisoformat(
            timestamp_text.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is not None:
            timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)

        vehicle_count = int(data["vehicle_count"])
        avg_speed = float(data["avg_speed_kmh"])
        direction = data["direction"]

        if intersection_id not in {
            f"IN_{i:03d}" for i in range(1, 9)
        }:
            raise ValueError("Invalid intersection ID")

        if vehicle_count < 0 or not 0 <= avg_speed <= 120:
            raise ValueError("Invalid vehicle count or average speed")

        if direction not in ("N-S", "E-W"):
            raise ValueError("Invalid direction")

        congestion_level = (
            "high" if vehicle_count >= 55 or avg_speed < 20
            else "medium" if vehicle_count >= 30 or avg_speed < 35
            else "low"
        )

        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO traffic_data
                (intersection_id, timestamp, vehicle_count,
                 avg_speed_kmh, congestion_level, direction)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    intersection_id,
                    timestamp,
                    vehicle_count,
                    avg_speed,
                    congestion_level,
                    direction
                )
            )

        conn.commit()
        print(f"Saved to PostgreSQL: {intersection_id} | "
              f"Vehicles: {vehicle_count} | "
              f"Speed: {avg_speed} km/h | "
              f"Congestion: {congestion_level}")

    except Exception as error:
        conn.rollback()
        print(f"Error processing message: {error}")

def main():
    global conn

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Connected to PostgreSQL.")

        client = mqtt.Client()
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(BROKER, PORT, 60)
        print("Waiting for traffic readings. Press Ctrl+C to stop.")
        client.loop_forever()

    except KeyboardInterrupt:
        print("\nIngestion stopped.")

    except Exception as error:
        print(f"Startup error: {error}")

    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    main()