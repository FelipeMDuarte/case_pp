from fastapi import Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import get_settings


def get_database(request: Request) -> AsyncIOMotorDatabase:
    settings = get_settings()
    return request.app.state.mongo_client[settings.mongo_db]
