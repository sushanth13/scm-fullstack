import os
from kafka import KafkaConsumer
import json
import time
from pymongo import MongoClient

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "scmxpertlite")

print("🔌 Connecting to Kafka at:", KAFKA_BROKER)

# Retry loop
for i in range(5):
    try:
        consumer = KafkaConsumer(
            "sensor_data",
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
        )
        print("✅ Kafka Consumer connected")
        break
    except Exception as e:
        print(f"❌ Kafka connection failed (attempt {i+1}): {e}")
        time.sleep(5)
else:
    print("❌ Failed to connect to Kafka after retries")
    exit(1)

mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
collection = db.devices

print("📡 Waiting for Kafka messages...")

for message in consumer:
    data = message.value
    collection.insert_one({
        "deviceId": data.get("Device_ID"),
        "data": data,
    })
    print("📥 Inserted:", data)
