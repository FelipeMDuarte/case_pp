from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.utils import (
    dangling_reference_message,
    duplicate_message,
    not_found_message,
    query_filters,
    summarize_schema_change,
    write_audit_event,
    write_schema_version,
)
from app.connectors.abstract_connector import DuplicateError
from app.db import ConnectorFactory, get_connector_factory

# Primeiro função para endpoints read-only, depois função para endpoints com escrita, reutilizando a primeira.
def build_read_only_router(collection_name: str, out_model: type[BaseModel]) -> APIRouter:
    router = APIRouter(prefix=f"/{collection_name}", tags=[collection_name])

    @router.get("", response_model=list[out_model])
    async def list_all(
        request: Request,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        connector_factory: ConnectorFactory = Depends(get_connector_factory),
    ):
        connector = connector_factory(collection_name)
        return await connector.list(skip, limit, filters=query_filters(request))

    @router.get("/{item_id}", response_model=out_model)
    async def get_one(item_id: str, connector_factory: ConnectorFactory = Depends(get_connector_factory)):
        connector = connector_factory(collection_name)
        doc = await connector.get(item_id)
        if not doc:
            raise HTTPException(404, not_found_message(collection_name, item_id))
        return doc

    return router


def build_crud_router(
    collection_name: str,
    create_model: type[BaseModel],
    update_model: type[BaseModel],
    out_model: type[BaseModel],
    log_audit: bool = False,
    track_schema: bool = False,
    validate_refs: dict[str, str] | None = None,  # para validar referencias de urn
) -> APIRouter:
    router = build_read_only_router(collection_name, out_model)

    @router.post("", response_model=out_model, status_code=201)
    async def create(payload: create_model, connector_factory: ConnectorFactory = Depends(get_connector_factory)):  # type: ignore[valid-type]
        if validate_refs:
            for field, ref_collection in validate_refs.items():
                urn = getattr(payload, field)
                ref_connector = connector_factory(ref_collection)
                if not await ref_connector.exists("urn", urn):
                    raise HTTPException(422, dangling_reference_message(field, urn, ref_collection))
        connector = connector_factory(collection_name)
        try:
            doc = await connector.create(payload)
        except DuplicateError:
            raise HTTPException(409, duplicate_message(collection_name))
        if log_audit:
            await write_audit_event(connector_factory, doc["urn"], "CREATED", list(payload.model_dump().keys()))
        if track_schema and doc.get("structure"):
            columns = doc["structure"]["columns"]
            summary = f"estrutura inicial ({len(columns)} coluna(s))"
            await write_schema_version(connector_factory, doc["urn"], doc["structure"], change_summary=summary)
        return doc

    @router.patch("/{item_id}", response_model=out_model)
    async def update(
        item_id: str, payload: update_model, connector_factory: ConnectorFactory = Depends(get_connector_factory)  # type: ignore[valid-type]
    ):
        connector = connector_factory(collection_name)
        old_doc = await connector.get(item_id) if track_schema else None
        doc = await connector.update(item_id, payload)
        if not doc:
            raise HTTPException(404, not_found_message(collection_name, item_id))
        changed_fields = list(payload.model_dump(exclude_unset=True).keys())
        if log_audit and changed_fields:
            await write_audit_event(connector_factory, doc["urn"], "UPDATED", changed_fields)
        if track_schema and "structure" in changed_fields:
            old_columns = ((old_doc or {}).get("structure") or {}).get("columns", [])
            new_columns = (doc.get("structure") or {}).get("columns", [])
            summary = summarize_schema_change(old_columns, new_columns)
            await write_schema_version(connector_factory, doc["urn"], doc.get("structure"), change_summary=summary)
        return doc

    @router.delete("/{item_id}", status_code=204)
    async def delete(item_id: str, connector_factory: ConnectorFactory = Depends(get_connector_factory)):
        connector = connector_factory(collection_name)
        doc = await connector.get(item_id)
        if not doc:
            raise HTTPException(404, not_found_message(collection_name, item_id))
        await connector.delete(item_id)
        if log_audit:
            await write_audit_event(connector_factory, doc["urn"], "DELETED", [])

    return router
