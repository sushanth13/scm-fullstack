from kafka import KafkaProducer
import json
import random
import time
from datetime import datetime, timezone

TOPIC = "sensor_data"
BOOTSTRAP_SERVERS = "localhost:9092"

def generate_sensor_data():
    routes = ["Chennai", "Bengaluru", "Mumbai", "Delhi", "London", "New York"]

    route_from = random.choice(routes)
    route_to = random.choice(routes)
    while route_to == route_from:
        route_to = random.choice(routes)

    return {
        "Device_ID": random.randint(1150, 1160),
        "Battery_Level": round(random.uniform(2.5, 5.0), 2),
        "First_Sensor_temperature": round(random.uniform(10, 40), 1),
        "Humidity": round(random.uniform(30, 70), 1),
        "Route_From": route_from,
        "Route_To": route_to,
        "Timestamp": datetime.now(timezone.utc).isoformat(),
    }

def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("✅ Kafka Producer connected")
    print("🚀 Kafka Producer started. Sending sensor data...")

    try:
        while True:
            data = generate_sensor_data()
            producer.send(TOPIC, data)
            print(f"📤 Sent to Kafka: {data}")
            time.sleep(5)

    except KeyboardInterrupt:
        print("🛑 Producer stopped manually")

    finally:
        producer.close()
        print("🔒 Kafka Producer closed")

if __name__ == "__main__":
    main()

