"""
MongoDB connection manager
"""

# TODO: Implement MongoDB connection
# - Setup motor async client
# - Database connection pooling
# - Health check function
# - Graceful shutdown

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class MongoDB:
    client : AsyncIOMotorClient = None

db = MongoDB()

async def connect_db():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    print("Connected to MongoDB")

async def close_db():
    db.client.close()
    print("Closed MongoDB connection")

def get_database():
    return db.client[settings.MONGODB_DB_NAME]