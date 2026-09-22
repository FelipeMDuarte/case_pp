from datetime import datetime

from pydantic import BaseModel


class DataFlowCreate(BaseModel):
    source_urn: str
    target_urn: str
    transformation: str | None = None
    active: bool = True


class DataFlowUpdate(BaseModel):
    transformation: str | None = None
    active: bool | None = None


class DataFlowOut(DataFlowCreate):
    id: str
    created_at: datetime
    updated_at: datetime
