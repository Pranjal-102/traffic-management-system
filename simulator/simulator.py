import json
import time
import random
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "traffic/intersections"

INTERSECTIONS = [f"intersection_{i}" for i in range(1, 9)]

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

def generate_fake_data(intersection_id):
    return {
        "intersection_id": intersection_id,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "vehicle_count": random.randint(5, 80),
        "avg_speed_kmph": round(random.uniform(10, 60), 1),
        "congestion_level": random.choice(["low", "medium", "high"])
    }

print("Simulator started. Publishing every 5 seconds... (Ctrl+C to stop)")

try:
    while True:
        for intersection in INTERSECTIONS:
            data = generate_fake_data(intersection)
            payload = json.dumps(data)
            client.publish(TOPIC, payload)
            print(f"Published: {payload}")
        time.sleep(5)
except KeyboardInterrupt:
    print("Simulator stopped.")
    client.disconnect()