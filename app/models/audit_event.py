from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class EventType(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"


class AuditEventCreate(BaseModel):
    metadata_urn: str
    event_type: EventType
    occurred_at: datetime
    actor: str
    changed_fields: list[str] = []


class AuditEventOut(AuditEventCreate):
    id: str
