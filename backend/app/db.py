from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

# Globals set at startup
client = None
db = None
users_coll = None
shipments_coll = None
devices_coll = None


async def connect_to_mongo():
    global client, db, users_coll, shipments_coll, devices_coll

    # Use validated settings (no os.getenv)
    client = AsyncIOMotorClient(settings.MONGO_URL)

    # Attach DB + collections
    db = client[settings.DB_NAME]
    users_coll = db["users"]
    shipments_coll = db["shipments"]
    devices_coll = db["devices"]

    # Test connection
    await client.admin.command("ping")
    print("✅ Connected to MongoDB")


async def close_mongo():
    global client, db, users_coll, shipments_coll, devices_coll

    if client is not None:
        client.close()

    client = None
    db = None
    users_coll = None
    shipments_coll = None
    devices_coll = None


async def ensure_indexes():
    """
    Create indexes safely on startup.
    This function is idempotent.
    """
    if db is None:
        return

    if users_coll is not None:
        await users_coll.create_index("email", unique=True)

    if shipments_coll is not None:
        await shipments_coll.create_index("deviceId")

    if devices_coll is not None:
        await devices_coll.create_index("deviceId")

