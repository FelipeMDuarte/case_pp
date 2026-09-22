from datetime import datetime

from pydantic import BaseModel

from app.models.metadata import Column


class SchemaVersionCreate(BaseModel):
    metadata_urn: str
    columns: list[Column]
    change_summary: str | None = None
    detected_at: datetime


class SchemaVersionOut(SchemaVersionCreate):
    id: str
