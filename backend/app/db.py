from motor.motor_asyncio import AsyncIOMotorClient
import os

# Initialize client + collections globally (will be set at startup)
client = None
db = None
users_coll = None
shipments_coll = None
devices_coll = None

DB_NAME = os.getenv("DB_NAME")

async def connect_to_mongo():
    global client, db, users_coll, shipments_coll, devices_coll
    mongo_url = os.getenv("MONGO_URL")
    client = AsyncIOMotorClient(mongo_url)
    # attach database and collections
    db = client[DB_NAME]
    users_coll = db.get_collection("users")
    shipments_coll = db.get_collection("shipments")
    devices_coll = db.get_collection("devices")
    # Test connection
    await client.admin.command("ping")
    print("Connected to MongoDB")

async def close_mongo():
    global client, db, users_coll, shipments_coll, devices_coll
    if client:
        client.close()
    client = None
    db = None
    users_coll = None
    shipments_coll = None
    devices_coll = None

async def ensure_indexes():
    # create useful indexes if they don't exist
    try:
        if users_coll is not None:
            await users_coll.create_index("email", unique=True)
        if shipments_coll is not None:
            await shipments_coll.create_index([("deviceId", 1)])
        if devices_coll is not None:
            await devices_coll.create_index([("deviceId", 1)])
    except Exception:
        # If index creation fails, don't crash startup — log externally if needed
        pass