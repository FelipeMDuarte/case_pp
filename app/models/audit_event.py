from datetime import datetime

from pydantic import BaseModel


class AuditEventCreate(BaseModel):
    metadata_urn: str
    event_type: str  # CREATED | UPDATED | DELETED
    occurred_at: datetime
    actor: str
    changed_fields: list[str] = []


class AuditEventOut(AuditEventCreate):
    id: str
