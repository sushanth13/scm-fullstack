import json
import os
import time

from kafka import KafkaConsumer
from pymongo import MongoClient
from pymongo.errors import PyMongoError

consumer = KafkaConsumer(
    'sensor_data',
    bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),
    value_deserializer=lambda m: json.loads(m.decode('utf-8'))
)


def connect_devices_collection():
    mongo_url = os.getenv("MONGO_URL", "mongodb+srv://janasushanth_db_user:jssushanth@cluster0.a4jzzou.mongodb.net/")
    db_name = os.getenv("DB_NAME", "scmxpertlite")

    while True:
        try:
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            return client[db_name]["devices"]
        except PyMongoError as error:
            print(f"MongoDB connection failed: {error}. Retrying in 5 seconds...")
            time.sleep(5)


devices_coll = connect_devices_collection()

print("Kafka consumer started. Waiting for messages...")

for message in consumer:
    data = dict(message.value or {})
    payload = data.get("data") if isinstance(data.get("data"), dict) else data

    if "Humidity" not in data:
        humidity = payload.get("Humidity")
        if humidity is None:
            humidity = payload.get("humidity")
        if humidity is not None:
            data["Humidity"] = humidity

    timestamp = data.get("ts")
    if timestamp is None:
        timestamp = data.get("Timestamp")
    if timestamp is None:
        timestamp = payload.get("ts")
    if timestamp is None:
        timestamp = payload.get("Timestamp")
    if timestamp is None:
        timestamp = time.time()

    data["Timestamp"] = timestamp
    data["ts"] = timestamp

    while True:
        try:
            devices_coll.insert_one(data)
            print(f"Inserted into MongoDB: {data}")
            break
        except PyMongoError as error:
            print(f"MongoDB insert failed: {error}. Reconnecting and retrying...")
            time.sleep(5)
            devices_coll = connect_devices_collection()
