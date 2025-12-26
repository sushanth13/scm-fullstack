import json
from aiokafka import AIOKafkaProducer
from .config import settings
class KafkaProducer:
    def __init__(self, bootstrap_servers: str | None = None):
        self.bootstrap = bootstrap_servers or settings.KAFKA_BOOTSTRAP
        self._producer = None
    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap)
            await self._producer.start()
    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
    async def send(self, topic: str, value: dict, key: bytes | None = None):
        if self._producer is None:
            await self.start()
        payload = json.dumps(value, default=str).encode("utf-8")
        await self._producer.send_and_wait(topic, payload, key=key)
kafka_producer = KafkaProducer()
