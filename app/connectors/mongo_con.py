from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel
from pymongo import ReturnDocument

from app.connectors.abstract_connector import AbstractConnector


class MongoConnector(AbstractConnector):
    def __init__(self, db: AsyncIOMotorDatabase, collection_name: str) -> None:
        self.collection = db[collection_name]

    async def create(self, payload: BaseModel) -> dict:
        now = utcnow()
        doc = {**payload.model_dump(), "created_at": now, "updated_at": now}
        await self.collection.insert_one(doc)  # preenche doc["_id"] no próprio dict
        return serialize(doc)

    async def get(self, id: str) -> dict | None:
        oid = to_object_id(id)
        if oid is None:
            return None
        doc = await self.collection.find_one({"_id": oid})
        return serialize(doc) if doc else None

    async def list(self, skip: int = 0, limit: int = 100, filters: dict[str, str] | None = None) -> list[dict]:
        cursor = self.collection.find().sort("created_at", -1)
        docs = [serialize(doc) async for doc in cursor]
        if filters:
            docs = [doc for doc in docs if matches(doc, filters)]
        return docs[skip : skip + limit]

    async def update(self, id: str, payload: BaseModel) -> dict | None:
        oid = to_object_id(id)
        if oid is None:
            return None

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return await self.get(id)

        changes["updated_at"] = utcnow()
        doc = await self.collection.find_one_and_update(
            {"_id": oid}, {"$set": changes}, return_document=ReturnDocument.AFTER
        )
        return serialize(doc) if doc else None

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


def matches(doc: dict, filters: dict[str, str]) -> bool:
    for field, value in filters.items():
        actual = doc
        for part in field.split("."):
            actual = actual.get(part) if isinstance(actual, dict) else None
        if actual is None or value.lower() not in str(actual).lower():
            return False
    return True


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
