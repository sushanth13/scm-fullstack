import json
import os
import random
import time

from kafka import KafkaProducer

producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

route = ['Newyork,USA', 'Chennai, India', 'Bengaluru, India', 'London,UK']

while True:
    routefrom = random.choice(route)
    routeto = random.choice(route)
    if routefrom != routeto:
        timestamp = time.time()
        data = {
            "Battery_Level": round(random.uniform(2.0, 5.0), 2),
            "Device_ID": random.randint(1150, 1158),
            "First_Sensor_temperature": round(random.uniform(10, 40.0), 1),
            "Humidity": round(random.uniform(40.0, 80.0), 1),
            "Route_From": routefrom,
            "Route_To": routeto,
            "Timestamp": timestamp,
            "ts": timestamp,
        }
        producer.send('sensor_data', value=data)
        producer.flush()
        print(f"Sent to Kafka: {data}")
        time.sleep(10)
