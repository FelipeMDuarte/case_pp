from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.connectors.abstract_connector import AbstractConnector, DuplicateError


class MongoConnector(AbstractConnector):
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.collection = db[collection_name]

    async def create(self, payload: BaseModel) -> dict:
        now = utcnow()
        doc = {**payload.model_dump(), "created_at": now, "updated_at": now}
        try:
            await self.collection.insert_one(doc)  # preenche doc["_id"] no próprio dict
        except DuplicateKeyError as exc:
            raise DuplicateError(str(exc)) from exc
        return serialize(doc)

    async def get(self, id: str) -> dict | None:
        oid = to_object_id(id)
        if oid is None:
            return None
        doc = await self.collection.find_one({"_id": oid})
        return serialize(doc) if doc else None

    async def list(self, skip: int = 0, limit: int = 100, filters: dict[str, str] | None = None) -> list[dict]:
        cursor = self.collection.find(filters or {}).sort("created_at", -1).skip(skip).limit(limit)
        return [serialize(doc) async for doc in cursor]

    async def count(self, filters: dict[str, str] | None = None) -> int:
        return await self.collection.count_documents(filters or {})

    async def set_fields(self, id: str, fields: dict) -> dict | None:
        oid = to_object_id(id)
        if oid is None:
            return None
        doc = await self.collection.find_one_and_update(
            {"_id": oid}, {"$set": {**fields, "updated_at": utcnow()}}, return_document=ReturnDocument.AFTER
        )
        return serialize(doc) if doc else None

    async def delete(self, id: str) -> bool:
        oid = to_object_id(id)
        if oid is None:
            return False
        result = await self.collection.delete_one({"_id": oid})
        return result.deleted_count == 1

    async def exists(self, field: str, value: str) -> bool:
        return await self.collection.find_one({field: value}) is not None


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
