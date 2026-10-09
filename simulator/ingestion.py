import json
import os

import paho.mqtt.client as mqtt
import psycopg2
from dotenv import load_dotenv


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# MQTT CONFIGURATION
# ============================================================

BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))

MQTT_TOPIC = "traffic/readings/#"


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "traffic_db"),
    "user": os.getenv("DB_USER", "traffic_user"),
    "password": os.getenv("DB_PASSWORD", "traffic123"),
    "port": int(os.getenv("DB_PORT", "5432"))
}


# ============================================================
# VALID INTERSECTION IDs
# ============================================================

VALID_INTERSECTIONS = {
    "IN_001",
    "IN_002",
    "IN_003",
    "IN_004",
    "IN_005",
    "IN_006",
    "IN_007",
    "IN_008"
}


# ============================================================
# DATABASE CONNECTION
# ============================================================

try:

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Connected to PostgreSQL successfully.")

except Exception as e:

    print("ERROR: Could not connect to PostgreSQL.")
    print(f"Reason: {e}")

    raise SystemExit(1)


# ============================================================
# MQTT CALLBACK
# ============================================================

def on_connect(client, userdata, flags, rc):

    if rc == 0:

        print("Connected to MQTT broker.")

        client.subscribe(MQTT_TOPIC)

        print(f"Subscribed to: {MQTT_TOPIC}")

    else:

        print(
            f"MQTT connection failed with return code: {rc}"
        )


# ============================================================
# MESSAGE PROCESSING
# ============================================================

def on_message(client, userdata, msg):

    try:

        # ----------------------------------------------------
        # Decode MQTT message
        # ----------------------------------------------------

        payload = msg.payload.decode("utf-8")

        data = json.loads(payload)

        print("")
        print(f"[RECEIVED] Topic: {msg.topic}")
        print(f"Data: {data}")


        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        required_fields = [
            "intersection_id",
            "timestamp",
            "vehicle_count",
            "avg_speed_kmh",
            "direction"
        ]


        for field in required_fields:

            if field not in data:

                raise ValueError(
                    f"Missing required field: {field}"
                )


        # ----------------------------------------------------
        # Validate intersection ID
        # ----------------------------------------------------

        intersection_id = data["intersection_id"]

        if intersection_id not in VALID_INTERSECTIONS:

            raise ValueError(
                f"Invalid intersection_id: {intersection_id}"
            )


        # ----------------------------------------------------
        # Validate direction
        # ----------------------------------------------------

        direction = data["direction"]

        if direction not in ["N-S", "E-W"]:

            raise ValueError(
                f"Invalid direction: {direction}"
            )


        # ----------------------------------------------------
        # Validate vehicle count
        # ----------------------------------------------------

        vehicle_count = data["vehicle_count"]

        if not isinstance(vehicle_count, int):

            raise ValueError(
                "vehicle_count must be an integer"
            )

        if vehicle_count < 0:

            raise ValueError(
                "vehicle_count cannot be negative"
            )


        # ----------------------------------------------------
        # Validate average speed
        # ----------------------------------------------------

        avg_speed = float(data["avg_speed_kmh"])

        if not 0 <= avg_speed <= 120:

            raise ValueError(
                "avg_speed_kmh must be between 0 and 120"
            )


        # ----------------------------------------------------
        # Insert into PostgreSQL
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO readings
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
                intersection_id,
                data["timestamp"],
                vehicle_count,
                avg_speed,
                direction
            )
        )


        # Save transaction
        conn.commit()


        print(
            f"[INSERTED] {intersection_id} → "
            f"PostgreSQL readings table"
        )


    except Exception as e:

        # Rollback failed transaction
        conn.rollback()

        print(
            f"[ERROR] Could not process message: {e}"
        )


# ============================================================
# CREATE MQTT CLIENT
# ============================================================

client = mqtt.Client()

client.on_connect = on_connect
client.on_message = on_message


# ============================================================
# CONNECT TO MQTT BROKER
# ============================================================

print("")
print("=" * 60)
print("TRAFFIC MANAGEMENT SYSTEM - INGESTION")
print("=" * 60)

print(f"MQTT Broker : {BROKER}")
print(f"MQTT Port   : {PORT}")
print(f"MQTT Topic  : {MQTT_TOPIC}")
print("")


try:

    print("Connecting to MQTT broker...")

    client.connect(BROKER, PORT, 60)

except Exception as e:

    print("ERROR: Could not connect to MQTT broker.")
    print(f"Reason: {e}")

    cursor.close()
    conn.close()

    raise SystemExit(1)


# ============================================================
# START LISTENING
# ============================================================

print("Listening for traffic messages...")
print("Press Ctrl+C to stop.")
print("=" * 60)


try:

    client.loop_forever()


except KeyboardInterrupt:

    print("")
    print("Ingestion stopped by user.")


finally:

    client.disconnect()

    cursor.close()
    conn.close()

    print("Disconnected from MQTT broker.")
    print("Database connection closed.")