import json
import paho.mqtt.client as mqtt
import psycopg2

BROKER = "localhost"
PORT = 1883
TOPIC = "traffic/intersections"

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

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with code", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        cursor.execute(
            """INSERT INTO traffic_data 
               (intersection_id, timestamp, vehicle_count, avg_speed_kmph, congestion_level)
               VALUES (%s, %s, %s, %s, %s)""",
            (data["intersection_id"], data["timestamp"], data["vehicle_count"],
             data["avg_speed_kmph"], data["congestion_level"])
        )
        conn.commit()
        print(f"Inserted: {data}")
    except Exception as e:
        print(f"Error processing message: {e}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
print("Listening for messages... (Ctrl+C to stop)")
client.loop_forever()