from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.api.crud import build_crud_router
from app.connectors.mongo_con import MongoConnector
from app.db import get_database
from app.models.audit_event import AuditEventOut
from app.models.data_flow import DataFlowCreate, DataFlowOut, DataFlowUpdate
from app.models.metadata import MetadataCreate, MetadataOut, MetadataUpdate

metadata_router = build_crud_router("metadata", MetadataCreate, MetadataUpdate, MetadataOut, log_audit=True)
data_flow_router = build_crud_router("data_flows", DataFlowCreate, DataFlowUpdate, DataFlowOut)

# audit_events não usa build_crud_router: não tem POST/PATCH/DELETE, só é alimentado
# internamente pelo metadata_router (log_audit=True acima) e exposto aqui só pra leitura.
audit_events_router = APIRouter(prefix="/audit_events", tags=["audit_events"])


@audit_events_router.get("", response_model=list[AuditEventOut])
async def list_audit_events(skip: int = 0, limit: int = 100, db: AsyncIOMotorDatabase = Depends(get_database)):
    connector = MongoConnector(db, "audit_events")
    return await connector.list(skip, limit)


@audit_events_router.get("/{event_id}", response_model=AuditEventOut)
async def get_audit_event(event_id: str, db: AsyncIOMotorDatabase = Depends(get_database)):
    connector = MongoConnector(db, "audit_events")
    doc = await connector.get(event_id)
    if not doc:
        raise HTTPException(404, "Not found")
    return doc


all_routers = [metadata_router, data_flow_router, audit_events_router]

# pra adicionar um novo recurso genérico:
#
# from app.models.user import UserCreate, UserOut, UserUpdate
# user_router = build_crud_router("users", UserCreate, UserUpdate, UserOut)
# all_routers.append(user_router)
