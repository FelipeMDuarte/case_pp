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
        if not filters: # paginate do banco
            cursor = self.collection.find().sort("created_at", -1).skip(skip).limit(limit)
            return [serialize(doc) async for doc in cursor]

        cursor = self.collection.find().sort("created_at", -1)
        docs = [serialize(doc) async for doc in cursor]
        docs = [doc for doc in docs if matches(doc, filters)]
        return docs[skip : skip + limit]

    async def count(self, filters: dict[str, str] | None = None) -> int:
        if not filters:
            return await self.collection.count_documents({})
        cursor = self.collection.find()
        docs = [serialize(doc) async for doc in cursor]
        return sum(1 for doc in docs if matches(doc, filters))

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
