from kafka import KafkaConsumer
from pymongo import MongoClient
import json
import time
import sys

# ================================
# CONFIG
# ================================
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "sensor_data"

MONGO_URL = "mongodb+srv://janasushanth_db_user:jssushanth@cluster0.a4jzzou.mongodb.net/"
DB_NAME = "scmxpertlite"
COLLECTION_NAME = "device_telemetry"

# ================================
# KAFKA CONNECTION
# ================================
def connect_kafka(max_retries=5):
    for attempt in range(1, max_retries + 1):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BROKER,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="scmxpert-consumer-group"
            )
            print("✅ Connected to Kafka")
            return consumer
        except Exception as e:
            print(f"❌ Kafka connection failed (attempt {attempt}): {e}")
            time.sleep(5)

    print("❌ Failed to connect to Kafka after retries")
    sys.exit(1)

# ================================
# MONGODB CONNECTION
# ================================
def connect_mongodb():
    try:
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Test connection
        client.admin.command("ping")

        print("✅ Connected to MongoDB")
        print(f"📦 Database: {DB_NAME}, Collection: {COLLECTION_NAME}")

        return collection

    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        sys.exit(1)

# ================================
# MAIN
# ================================
def main():
    consumer = connect_kafka()
    collection = connect_mongodb()

    print("🚀 Kafka consumer started. Waiting for messages...\n")

    try:
        for message in consumer:
            data = message.value
            data["kafka_offset"] = message.offset
            data["kafka_partition"] = message.partition
            data["ingested_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

            collection.insert_one(data)
            print(f"📥 Inserted into MongoDB: {data}")

    except KeyboardInterrupt:
        print("\n🛑 Consumer stopped manually")
    except Exception as e:
        print(f"❌ Error while consuming messages: {e}")
    finally:
        consumer.close()
        print("🔒 Kafka consumer closed")

# ================================
# ENTRY POINT
# ================================
if __name__ == "__main__":
    main()
