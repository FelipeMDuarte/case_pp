from datetime import datetime, timezone

from fastapi import Request

from app.db import ConnectorFactory
from app.models.audit_event import AuditEventCreate
from app.models.schema_version import SchemaVersionCreate


def query_filters(request: Request) -> dict[str, str]:
    # skip e limit removidos porque não são filtros, aceita notação de ponto "asset.domain"
    return {key: value for key, value in request.query_params.items() if key not in ("skip", "limit")}


async def write_audit_event(
    connector_factory: ConnectorFactory, urn: str, event_type: str, changed_fields: list[str]
) -> None:
    connector = connector_factory("audit_events")
    await connector.create(
        AuditEventCreate(
            metadata_urn=urn,
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            actor="api",  # sem autenticação para o case, sistema real seria usuário logado por exemplo
            changed_fields=changed_fields,
        )
    )


async def write_schema_version(
    connector_factory: ConnectorFactory, urn: str, structure: dict, change_summary: str | None = None
) -> None:
    connector = connector_factory("schema_versions")
    await connector.create(
        SchemaVersionCreate(
            metadata_urn=urn,
            columns=structure["columns"],
            change_summary=change_summary,
            detected_at=datetime.now(timezone.utc),
        )
    )


def summarize_schema_change(old_columns: list[dict], new_columns: list[dict]) -> str:
    old_types = {c["name"]: c["data_type"] for c in old_columns}
    new_types = {c["name"]: c["data_type"] for c in new_columns}

    added = sorted(set(new_types) - set(old_types))
    removed = sorted(set(old_types) - set(new_types))
    changed_type = sorted(name for name in set(old_types) & set(new_types) if old_types[name] != new_types[name])

    parts = []
    if added:
        parts.append(f"coluna(s) adicionada(s): {', '.join(added)}")
    if removed:
        parts.append(f"coluna(s) removida(s): {', '.join(removed)}")
    if changed_type:
        parts.append(f"tipo alterado: {', '.join(changed_type)}")
    return "; ".join(parts) if parts else "estrutura atualizada"
