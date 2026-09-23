from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.metadata import (
    AssetEnvironment,
    AssetStatus,
    AssetType,
    BusinessMetadata,
    Layer,
    OwnerType,
    QualityStatus,
    SecurityAndPrivacy,
    TableStructure,
)

# campos obrigatórios em create/out viram opcionais aqui pra permitir merge parcial:
# omitir o campo é válido, mandar null explícito não é


class AssetInfoUpdate(BaseModel):
    name: str = None  # type: ignore[assignment]
    display_name: str | None = None
    description: str | None = None
    asset_type: AssetType = None  # type: ignore[assignment]
    environment: AssetEnvironment = None  # type: ignore[assignment]
    status: AssetStatus = None  # type: ignore[assignment]
    domain: str | None = None
    layer: Layer | None = None
    tags: list[str] = None  # type: ignore[assignment]


class SourceUpdate(BaseModel):
    platform: str = None  # type: ignore[assignment]
    fully_qualified_name: str = None  # type: ignore[assignment]


class OwnerUpdate(BaseModel):
    type: OwnerType = None  # type: ignore[assignment]
    name: str = None  # type: ignore[assignment]
    contact: str = None  # type: ignore[assignment]


class OwnershipUpdate(BaseModel):
    business_owner: OwnerUpdate | None = None
    technical_owner: OwnerUpdate = None  # type: ignore[assignment]
    data_steward: OwnerUpdate | None = None


class QualityUpdate(BaseModel):
    status: QualityStatus = None  # type: ignore[assignment]
    score: float = Field(default=None, ge=0, le=1)  # type: ignore[assignment]
    checked_at: datetime = None  # type: ignore[assignment]
    issues: list[str] = None  # type: ignore[assignment]


class MetadataUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"security_and_privacy": {"sensitivity": "RESTRICTED"}}]}
    )
    asset: AssetInfoUpdate = None  # type: ignore[assignment]
    source: SourceUpdate = None  # type: ignore[assignment]
    business_metadata: BusinessMetadata = None  # type: ignore[assignment]
    ownership: OwnershipUpdate = None  # type: ignore[assignment]
    security_and_privacy: SecurityAndPrivacy = None  # type: ignore[assignment]
    quality: QualityUpdate | None = None
    structure: TableStructure | None = None
    last_reviewed_at: datetime | None = None
