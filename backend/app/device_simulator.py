import asyncio
import httpx
import argparse
import os
import time
import random

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

async def run(device_id: str, interval: float):
    async with httpx.AsyncClient() as client:
        while True:
            payload = {
                "deviceId": device_id,
                "ts": int(time.time()),
                "temp": round(20 + random.random() * 10, 2),
                "battery": round(random.random() * 100, 2)
            }
            url = f"{API_BASE}/device/{device_id}/publish"
            await client.post(url, json=payload)
            print("Sent:", payload)
            await asyncio.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="dev-1")
    parser.add_argument("--interval", type=float, default=1.0)
    args = parser.parse_args()

    asyncio.run(run(args.device, args.interval))
