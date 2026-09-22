from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.connectors.mongo_con import MongoConnector
from app.db import get_database
from app.models.audit_event import AuditEventCreate


async def write_audit_event(db: AsyncIOMotorDatabase, urn: str, event_type: str, changed_fields: list[str]) -> None:
    connector = MongoConnector(db, "audit_events")
    await connector.create(
        AuditEventCreate(
            metadata_urn=urn,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            actor="api",  # sem autenticação neste case; num sistema real viria do usuário/serviço autenticado
            changed_fields=changed_fields,
        )
    )


def build_crud_router(
    collection_name: str,
    create_model: type[BaseModel],
    update_model: type[BaseModel],
    out_model: type[BaseModel],
    log_audit: bool = False,
) -> APIRouter:
    router = APIRouter(prefix=f"/{collection_name}", tags=[collection_name])

    @router.post("", response_model=out_model, status_code=201)
    async def create(payload: create_model, db: AsyncIOMotorDatabase = Depends(get_database)):  # type: ignore[valid-type]
        connector = MongoConnector(db, collection_name)
        doc = await connector.create(payload)
        if log_audit:
            await write_audit_event(db, doc["urn"], "CREATED", list(payload.model_dump().keys()))
        return doc

    @router.get("", response_model=list[out_model])
    async def list_all(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_database)):
        connector = MongoConnector(db, collection_name)
        return await connector.list(skip, limit)

    @router.get("/{item_id}", response_model=out_model)
    async def get_one(item_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
        connector = MongoConnector(db, collection_name)
        doc = await connector.get(item_id)
        if not doc:
            raise HTTPException(404, "Not found")
        return doc

    @router.patch("/{item_id}", response_model=out_model)
    async def update(item_id: str, payload: update_model, db: AsyncIOMotorDatabase = Depends(get_database)):  # type: ignore[valid-type]
        connector = MongoConnector(db, collection_name)
        doc = await connector.update(item_id, payload)
        if not doc:
            raise HTTPException(404, "Not found")
        changed_fields = list(payload.model_dump(exclude_unset=True).keys())
        if log_audit and changed_fields:
            await write_audit_event(db, doc["urn"], "UPDATED", changed_fields)
        return doc

    @router.delete("/{item_id}", status_code=204)
    async def delete(item_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
        connector = MongoConnector(db, collection_name)
        doc = await connector.get(item_id)
        if not doc:
            raise HTTPException(404, "Not found")
        await connector.delete(item_id)
        if log_audit:
            await write_audit_event(db, doc["urn"], "DELETED", [])

    return router
