# app/kafka.py

class KafkaProducerStub:
    async def start(self):
        print("Kafka producer stub started")

    async def stop(self):
        print("Kafka producer stub stopped")


kafka_producer = KafkaProducerStub()