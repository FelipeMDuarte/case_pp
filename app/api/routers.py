from app.api.crud import build_crud_router, build_read_only_router
from app.models.audit_event import AuditEventOut
from app.models.data_flow import DataFlowCreate, DataFlowOut, DataFlowUpdate
from app.models.metadata import MetadataCreate, MetadataOut
from app.models.metadata_update import MetadataUpdate
from app.models.schema_version import SchemaVersionOut

# CRUD inteiro
metadata_router = build_crud_router(
    "metadata",
    MetadataCreate,
    MetadataUpdate,
    MetadataOut,
    log_audit=True,
    track_schema=True,
    soft_delete={"asset.status": "DEPRECATED"},
)
data_flow_router = build_crud_router(
    "data_flows",
    DataFlowCreate,
    DataFlowUpdate,
    DataFlowOut,
    validate_refs={"source_urn": "metadata", "target_urn": "metadata"},
    forbid_self_reference=("source_urn", "target_urn"),
)

# Read-only
audit_events_router = build_read_only_router("audit_events", AuditEventOut)
schema_versions_router = build_read_only_router("schema_versions", SchemaVersionOut)

all_routers = [metadata_router, data_flow_router, audit_events_router, schema_versions_router]
