import json
import time
import random
import os
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# MQTT configuration
BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))


# All intersections defined in the project
INTERSECTIONS = [
    "IN_001",
    "IN_002",
    "IN_003",
    "IN_004",
    "IN_005",
    "IN_006",
    "IN_007",
    "IN_008"
]


def generate_fake_data(intersection_id):
    """
    Generate one simulated traffic reading.

    The generated data follows JSON_CONTRACT.md.
    """

    direction = random.choice(["N-S", "E-W"])

    data = {
        "intersection_id": intersection_id,
        "timestamp": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "vehicle_count": random.randint(5, 80),
        "avg_speed_kmh": round(random.uniform(10, 60), 1),
        "direction": direction
    }

    return data


# Create MQTT client
client = mqtt.Client()


print("=" * 60)
print("TRAFFIC MANAGEMENT SYSTEM - SIMULATOR")
print("=" * 60)

print(f"MQTT Broker : {BROKER}")
print(f"MQTT Port   : {PORT}")
print("")


# Connect to MQTT broker
print("Connecting to MQTT broker...")

try:
    client.connect(BROKER, PORT, 60)
except Exception as e:
    print(f"ERROR: Could not connect to MQTT broker.")
    print(f"Reason: {e}")
    print("")
    print("Make sure the MQTT broker (Mosquitto) is running.")
    raise SystemExit(1)


print("Connected to MQTT broker.")
print("")
print("Simulator started.")
print("Publishing traffic data every 5 seconds.")
print("Press Ctrl+C to stop.")
print("=" * 60)


try:

    while True:

        for intersection_id in INTERSECTIONS:

            # Generate traffic data
            data = generate_fake_data(intersection_id)

            # MQTT topic
            topic = f"traffic/readings/{intersection_id}"

            # Convert dictionary to JSON
            payload = json.dumps(data)

            # Publish message
            result = client.publish(topic, payload)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:

                print(
                    f"[PUBLISHED] {intersection_id} | "
                    f"Direction: {data['direction']} | "
                    f"Vehicles: {data['vehicle_count']} | "
                    f"Speed: {data['avg_speed_kmh']} km/h"
                )

            else:

                print(
                    f"[ERROR] Failed to publish data "
                    f"for {intersection_id}"
                )

        print("-" * 60)

        # Wait before next batch
        time.sleep(5)


except KeyboardInterrupt:

    print("")
    print("Simulator stopped by user.")


finally:

    client.disconnect()
    print("Disconnected from MQTT broker.")