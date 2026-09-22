from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel


class MongoConnector:
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.collection = db[collection_name]

    async def create(self, payload: BaseModel) -> dict:
        now = utcnow()
        doc = {**payload.model_dump(), "created_at": now, "updated_at": now}
        result = await self.collection.insert_one(doc)
        return await self.get(str(result.inserted_id))

    async def get(self, id: str) -> dict | None:
        oid = to_object_id(id)
        if oid is None:
            return None
        doc = await self.collection.find_one({"_id": oid})
        return serialize(doc) if doc else None

    async def list(self, skip: int = 0, limit: int = 100) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
        return [serialize(doc) async for doc in cursor]

    async def update(self, id: str, payload: BaseModel) -> dict | None:
        oid = to_object_id(id)
        if oid is None:
            return None

        changes = payload.model_dump(exclude_unset=True)
        if changes:
            changes["updated_at"] = utcnow()
            await self.collection.update_one({"_id": oid}, {"$set": changes})

        return await self.get(id)

    async def delete(self, id: str) -> bool:
        oid = to_object_id(id)
        if oid is None:
            return False
        result = await self.collection.delete_one({"_id": oid})
        return result.deleted_count == 1


def to_object_id(id: str) -> ObjectId | None:
    try:
        return ObjectId(id)
    except (InvalidId, TypeError):
        return None


def serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
