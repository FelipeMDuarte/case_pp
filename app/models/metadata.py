from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class OwnerType(StrEnum):
    PERSON = "PERSON"
    TEAM = "TEAM"


class Owner(BaseModel):
    type: OwnerType
    name: str
    contact: str


class AssetType(StrEnum):
    TABLE = "TABLE"
    VIEW = "VIEW"
    TOPIC = "TOPIC"
    FILE = "FILE"
    DASHBOARD = "DASHBOARD"
    MODEL = "MODEL"


class AssetEnvironment(StrEnum):
    DEVELOPMENT = "DEVELOPMENT"
    STAGING = "STAGING"
    PRODUCTION = "PRODUCTION"


class AssetStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DEPRECATED = "DEPRECATED"


class Layer(StrEnum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


class AssetInfo(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    asset_type: AssetType
    environment: AssetEnvironment
    status: AssetStatus = AssetStatus.ACTIVE
    domain: str | None = None
    layer: Layer | None = None
    tags: list[str] = []


class Source(BaseModel):
    platform: str  # livre de propósito: catálogo aceita qualquer plataforma, não é uma lista fechada
    fully_qualified_name: str


class BusinessMetadata(BaseModel):
    purpose: str | None = None
    grain: str | None = None


class Ownership(BaseModel):
    business_owner: Owner | None = None
    technical_owner: Owner
    data_steward: Owner | None = None


class Sensitivity(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class SecurityAndPrivacy(BaseModel):
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    contains_personal_data: bool = False
    regulations: list[str] = []  # livre: lista de regulamentações cresce (LGPD, GDPR, CCPA...)


class QualityStatus(StrEnum):
    PASSED = "PASSED"
    WARNING = "WARNING"
    FAILED = "FAILED"


class Quality(BaseModel):
    status: QualityStatus
    score: float = Field(ge=0, le=1)
    checked_at: datetime
    issues: list[str] = []


class Column(BaseModel):
    name: str
    data_type: str  # livre de propósito: tipo de coluna é específico de cada plataforma
    description: str | None = None


class TableStructure(BaseModel):
    columns: list[Column]


class MetadataCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "urn": "urn:data:bigquery:company-analytics-prod.sales.orders",
                    "asset": {
                        "name": "orders",
                        "display_name": "Pedidos",
                        "description": "Tabela analítica com um registro por pedido realizado pelos clientes.",
                        "asset_type": "TABLE",
                        "environment": "PRODUCTION",
                        "status": "ACTIVE",
                        "domain": "SALES",
                        "layer": "GOLD",
                        "tags": ["orders", "revenue"],
                    },
                    "source": {
                        "platform": "BIGQUERY",
                        "fully_qualified_name": "company-analytics-prod.sales.orders",
                    },
                    "business_metadata": {
                        "purpose": "Disponibilizar pedidos para análises de receita e comportamento de clientes.",
                        "grain": "Uma linha por pedido.",
                    },
                    "ownership": {
                        "business_owner": {
                            "type": "TEAM",
                            "name": "Sales Operations",
                            "contact": "sales-operations@example.com",
                        },
                        "technical_owner": {
                            "type": "TEAM",
                            "name": "Data Engineering",
                            "contact": "data-engineering@example.com",
                        },
                    },
                    "security_and_privacy": {
                        "sensitivity": "CONFIDENTIAL",
                        "contains_personal_data": True,
                        "regulations": ["LGPD"],
                    },
                    "structure": {
                        "columns": [
                            {"name": "order_id", "data_type": "STRING", "description": "Identificador único do pedido."},
                            {"name": "gross_amount", "data_type": "NUMERIC", "description": "Valor bruto do pedido."},
                        ]
                    },
                }
            ]
        }
    )

    urn: str
    asset: AssetInfo
    source: Source
    business_metadata: BusinessMetadata = BusinessMetadata()
    ownership: Ownership
    security_and_privacy: SecurityAndPrivacy = SecurityAndPrivacy()
    quality: Quality | None = None
    structure: TableStructure | None = None
    last_reviewed_at: datetime | None = None


class MetadataUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"security_and_privacy": {"sensitivity": "RESTRICTED"}}]}
    )

    asset: AssetInfo | None = None
    source: Source | None = None
    business_metadata: BusinessMetadata | None = None
    ownership: Ownership | None = None
    security_and_privacy: SecurityAndPrivacy | None = None
    quality: Quality | None = None
    structure: TableStructure | None = None
    last_reviewed_at: datetime | None = None


class MetadataOut(MetadataCreate):
    id: str
    created_at: datetime
    updated_at: datetime
