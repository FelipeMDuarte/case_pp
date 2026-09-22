from datetime import datetime

from pydantic import BaseModel


class Owner(BaseModel):
    type: str  # PERSON | TEAM
    name: str
    contact: str


class AssetInfo(BaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    asset_type: str  # TABLE, VIEW, TOPIC, FILE, DASHBOARD, MODEL
    environment: str  # DEVELOPMENT, STAGING, PRODUCTION
    status: str = "ACTIVE"  # ACTIVE, INACTIVE, DEPRECATED
    domain: str | None = None
    layer: str | None = None  # BRONZE, SILVER, GOLD
    tags: list[str] = []


class Source(BaseModel):
    platform: str
    fully_qualified_name: str


class BusinessMetadata(BaseModel):
    purpose: str | None = None
    grain: str | None = None


class Ownership(BaseModel):
    business_owner: Owner | None = None
    technical_owner: Owner
    data_steward: Owner | None = None


class SecurityAndPrivacy(BaseModel):
    sensitivity: str = "INTERNAL"  # PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    contains_personal_data: bool = False
    regulations: list[str] = []


class Quality(BaseModel):
    status: str  # PASSED, WARNING, FAILED
    score: float
    checked_at: datetime
    issues: list[str] = []


class MetadataCreate(BaseModel):
    urn: str
    asset: AssetInfo
    source: Source
    business_metadata: BusinessMetadata = BusinessMetadata()
    ownership: Ownership
    security_and_privacy: SecurityAndPrivacy = SecurityAndPrivacy()
    quality: Quality | None = None
    last_reviewed_at: datetime | None = None


class MetadataUpdate(BaseModel):
    asset: AssetInfo | None = None
    source: Source | None = None
    business_metadata: BusinessMetadata | None = None
    ownership: Ownership | None = None
    security_and_privacy: SecurityAndPrivacy | None = None
    quality: Quality | None = None
    last_reviewed_at: datetime | None = None


class MetadataOut(MetadataCreate):
    id: str
    created_at: datetime
    updated_at: datetime
