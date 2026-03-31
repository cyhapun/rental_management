import os
from motor.motor_asyncio import AsyncIOMotorClient
from functools import lru_cache
from dotenv import load_dotenv

# Load .env located in the same directory as this file
HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

class Settings:
    MONGO_URI: str
    MONGO_DB: str

    def __init__(self):
        self.MONGO_URI = os.getenv("MONGO_URI")
        self.MONGO_DB = os.getenv("MONGO_DB")


@lru_cache()
def get_settings():
    return Settings()


def get_client():
    settings = get_settings()
    return AsyncIOMotorClient(settings.MONGO_URI)


def get_db():
    settings = get_settings()
    client = get_client()
    if not settings.MONGO_DB:
        raise RuntimeError("MONGO_DB is not configured")
    return client[settings.MONGO_DB]
