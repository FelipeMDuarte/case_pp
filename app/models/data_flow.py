from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DataFlowCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source_urn": "urn:data:postgresql:commerce-prod.public.orders",
                    "target_urn": "urn:data:bigquery:company-analytics-prod.sales.orders",
                    "transformation": "Extração incremental por updated_at, normalização ou deduplicação.",
                }
            ]
        }
    )

    source_urn: str
    target_urn: str
    transformation: str | None = None
    active: bool = True


class DataFlowUpdate(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"active": False}]})

    transformation: str | None = None
    active: bool | None = None


class DataFlowOut(DataFlowCreate):
    id: str
    created_at: datetime
    updated_at: datetime
