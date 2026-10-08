import json
import time
import random
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


BROKER = "localhost"
PORT = 1883

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
    direction = random.choice(["N-S", "E-W"])

    data = {
        "intersection_id": intersection_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vehicle_count": random.randint(5, 80),
        "avg_speed_kmh": round(random.uniform(10, 60), 1),
        "direction": direction
    }

    return data


client = mqtt.Client()

print("Connecting to MQTT broker...")
client.connect(BROKER, PORT, 60)

print("Simulator started. Publishing every 5 seconds...")
print("Press Ctrl+C to stop.")

try:
    while True:

        for intersection_id in INTERSECTIONS:

            data = generate_fake_data(intersection_id)

            topic = f"traffic/readings/{intersection_id}"

            payload = json.dumps(data)

            result = client.publish(topic, payload)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"Published to {topic}: {payload}")
            else:
                print(f"Failed to publish to {topic}")

        time.sleep(5)

except KeyboardInterrupt:
    print("\nSimulator stopped.")
    client.disconnect()