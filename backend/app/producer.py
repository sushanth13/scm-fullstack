from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime

# ================================
# CONFIG
# ================================
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "sensor_data"

# ================================
# KAFKA PRODUCER
# ================================
def connect_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            retries=5
        )
        print("✅ Kafka Producer connected")
        return producer
    except Exception as e:
        print(f"❌ Kafka Producer connection failed: {e}")
        exit(1)

# ================================
# DATA GENERATORS
# ================================
route = ['Newyork,USA', 'Chennai, India', 'Bengaluru, India', 'London,UK']

DEVICE_IDS = list(range(1150, 1159))

def generate_sensor_data():
    route_from, route_to = random.choice(route).split(", ")

    return {
        "Device_ID": random.choice(DEVICE_IDS),
        "Battery_Level": round(random.uniform(2.5, 5.0), 2),
        "First_Sensor_temperature": round(random.uniform(8.0, 40.0), 1),
        "Humidity": round(random.uniform(30, 90), 1),
        "Route_From": route_from,
        "Route_To": route_to,
        "Timestamp": datetime.utcnow().isoformat()
    }

# ================================
# MAIN LOOP
# ================================
def main():
    producer = connect_producer()

    print("🚀 Kafka Producer started. Sending sensor data...\n")

    try:
        while True:
            data = generate_sensor_data()

            producer.send(KAFKA_TOPIC, data)
            producer.flush()

            print(f"📤 Sent to Kafka: {data}")

            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Producer stopped manually")
    finally:
        producer.close()
        print("🔒 Kafka Producer closed")

# ================================
# ENTRY POINT
# ================================
if __name__ == "__main__":
    main()
