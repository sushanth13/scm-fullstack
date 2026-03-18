import argparse
import asyncio
import os
import random
import time

import httpx

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api")


async def run(device_id: str, interval: float):
    async with httpx.AsyncClient() as client:
        while True:
            payload = {
                "deviceId": device_id,
                "ts": int(time.time()),
                "Battery_Level": round(random.random() * 100, 2),
                "First_Sensor_temperature": round(20 + random.random() * 10, 2),
                "Humidity": round(40 + random.random() * 30, 2),
                "Route_From": "Hyderabad",
                "Route_To": "Mumbai",
                "Timestamp": int(time.time()),
            }
            url = f"{API_BASE}/device/{device_id}/publish"
            response = await client.post(url, json=payload)
            response.raise_for_status()
            print("Sent:", payload)
            await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="DEV001")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    asyncio.run(run(args.device, args.interval))
