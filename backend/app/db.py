from motor.motor_asyncio import AsyncIOMotorClient # Async MongoDB client for non-blocking database operations (used in FastAPI async endpoints and background tasks)
from app.config import settings # For accessing configuration settings (e.g. database URL, JWT secret, etc.)

# Globals set at startup
client = None # MongoDB client instance (initialized on app startup, used for database operations throughout the app)
db = None
users_coll = None
shipments_coll = None
devices_coll = None


async def connect_to_mongo():
    global client, db, users_coll, shipments_coll, devices_coll

    # Use validated settings (no os.getenv)
    client = AsyncIOMotorClient(settings.MONGO_URL)

    # Attach DB + collections
    db = client[settings.DB_NAME] # Get database instance from MongoDB client using the configured database name (e.g. "scmxpertlite")
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

