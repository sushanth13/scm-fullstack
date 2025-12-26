import asyncio, json, yaml
from aiokafka import AIOKafkaConsumer
from .config import settings
from .db import get_db
from datetime import datetime
def load_mapping(path: str = "mapping.yml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
MAPPING = load_mapping()
def transform_event(topic: str, msg_value: dict):
    evt_type = msg_value.get("type","")
    payload = msg_value.get("payload",{})
    rule = MAPPING.get(evt_type) or {}
    target_collection = rule.get("collection","events")
    fields_map = rule.get("fields",{})
    doc = {}
    for tgt, src_path in fields_map.items():
        parts = src_path.split(".")
        cur = msg_value
        val = None
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                cur = None
                break
        val = cur
        transform_fn = rule.get("transforms",{}).get(tgt)
        if transform_fn == "to_int":
            try: val = int(val)
            except: pass
        elif transform_fn == "to_float":
            try: val = float(val)
            except: pass
        doc[tgt] = val
    doc["_meta"] = {"source": msg_value.get("source"), "event_type": evt_type, "kafka_topic": topic, "ingested_at": datetime.utcnow().isoformat()}
    if rule.get("keep_payload", True):
        doc["_payload"] = payload
    id_field = rule.get("id_field")
    if id_field and doc.get(id_field):
        doc["_id"] = doc.get(id_field)
    return {"collection": target_collection, "document": doc}
class KafkaConsumerWorker:
    def __init__(self, topic=None, bootstrap=None, group_id="scm-transformer-group"):
        self.topic = topic or settings.KAFKA_TOPIC
        self.bootstrap = bootstrap or settings.KAFKA_BOOTSTRAP
        self.group_id = group_id
        self._consumer = None; self._task = None; self._running = False
    async def start(self):
        self._consumer = AIOKafkaConsumer(self.topic, bootstrap_servers=self.bootstrap, group_id=self.group_id, auto_offset_reset="earliest", enable_auto_commit=True)
        await self._consumer.start()
        self._running = True; self._task = asyncio.create_task(self._consume_loop())
        print(f"Consumer started for {self.topic}")
    async def stop(self):
        self._running = False
        if self._task: await self._task
        if self._consumer: await self._consumer.stop(); self._consumer=None
    async def _consume_loop(self):
        db = get_db()
        try:
            async for msg in self._consumer:
                try:
                    raw = msg.value.decode("utf-8"); payload = json.loads(raw)
                except Exception:
                    payload = {"raw": msg.value.decode("utf-8")}
                try:
                    transformed = transform_event(msg.topic, payload)
                    coll_name = transformed.get("collection","events"); doc = transformed.get("document",{"_payload":payload})
                    collection = db[coll_name]; await collection.insert_one(doc); print("Inserted into", coll_name)
                except Exception as e:
                    print("Transform error:", e); await db["events"].insert_one({"kafka_topic": msg.topic, "payload": payload, "error": str(e)})
        except Exception as exc:
            print("Consumer loop error:", exc)
if __name__ == '__main__':
    import asyncio
    async def _main():
        w=KafkaConsumerWorker(); await w.start()
        try:
            while True: await asyncio.sleep(1)
        except KeyboardInterrupt: await w.stop()
    asyncio.run(_main())
