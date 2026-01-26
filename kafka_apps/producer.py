from kafka import KafkaProducer
import json
import random
import time
import os
from datetime import datetime, timezone

# ================================
# CONFIG (ENV-FIRST)
# ================================
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "sensor_data")

# ================================
# SENSOR DATA GENERATOR
# ================================
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

# ================================
# KAFKA PRODUCER CONNECT
# ================================
def connect_producer(max_retries=10):
    for attempt in range(1, max_retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                api_version_auto_timeout_ms=5000,
            )
            print("✅ Kafka Producer connected")
            return producer
        except Exception as e:
            print(f"❌ Kafka Producer connection failed (attempt {attempt}): {e}")
            time.sleep(5)

    raise RuntimeError("Kafka not available")


# ================================
# MAIN
# ================================
def main():
    producer = connect_producer()
    print("🚀 Kafka Producer started. Sending sensor data...\n")

    try:
        while True:
            data = generate_sensor_data()
            producer.send(TOPIC, data)
            producer.flush()

            print(f"📤 Sent to Kafka ({TOPIC}): {data}")
            time.sleep(5)

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
