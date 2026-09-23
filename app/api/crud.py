from typing import Generic, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ValidationError

from app.api.utils import (
    already_deleted_message,
    dangling_reference_message,
    deep_merge,
    duplicate_message,
    get_nested,
    invalid_filter_message,
    not_found_message,
    query_filters,
    self_reference_message,
    summarize_schema_change,
    validation_error_message,
    write_audit_event,
    write_schema_version,
)
from app.connectors.abstract_connector import DuplicateError
from app.db import ConnectorFactory, get_connector_factory

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int


# Primeiro função para endpoints read-only, depois função para endpoints com escrita, reutilizando a primeira.
def build_read_only_router(collection_name: str, out_model: type[BaseModel]) -> APIRouter:
    router = APIRouter(prefix=f"/{collection_name}", tags=[collection_name])

    @router.get("", response_model=Page[out_model])
    async def list_all(
        request: Request,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=100),
        connector_factory: ConnectorFactory = Depends(get_connector_factory),
    ):
        connector = connector_factory(collection_name)
        filters = query_filters(request)
        for key in filters:
            if "$" in key:
                raise HTTPException(422, invalid_filter_message(key))
        items = await connector.list(skip, limit, filters=filters)
        total = await connector.count(filters=filters)
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    @router.get("/{item_id}", response_model=out_model)
    async def get_one(item_id: str, connector_factory: ConnectorFactory = Depends(get_connector_factory)):
        connector = connector_factory(collection_name)
        doc = await connector.get(item_id)
        if not doc:
            raise HTTPException(404, not_found_message(collection_name, item_id))
        return doc

    return router


def merge_and_validate(old_doc: dict, changes: dict, out_model: type[BaseModel]) -> dict:
    merged_fields = {key: deep_merge(old_doc.get(key), value) for key, value in changes.items()}
    try:
        validated = out_model.model_validate({**old_doc, **merged_fields})
    except ValidationError as exc:
        raise HTTPException(422, validation_error_message(exc.errors())) from exc
    validated_dump = validated.model_dump()
    return {key: validated_dump[key] for key in merged_fields}


def build_crud_router(
    collection_name: str,
    create_model: type[BaseModel],
    update_model: type[BaseModel],
    out_model: type[BaseModel],
    log_audit: bool = False,
    track_schema: bool = False,
    validate_refs: dict[str, str] | None = None,  # para validar referencias de urn
    forbid_self_reference: tuple[str, str] | None = None,
    soft_delete: dict[str, str] | None = None,
) -> APIRouter:
    router = build_read_only_router(collection_name, out_model)

    @router.post("", response_model=out_model, status_code=201)
    async def create(
        payload: create_model,  # type: ignore[valid-type]
        response: Response,
        connector_factory: ConnectorFactory = Depends(get_connector_factory),
    ):
        if forbid_self_reference:
            field_a, field_b = forbid_self_reference
            if getattr(payload, field_a) == getattr(payload, field_b):
                raise HTTPException(422, self_reference_message(field_a, field_b))
        if validate_refs:
            for field, ref_collection in validate_refs.items():
                urn = getattr(payload, field)
                ref_connector = connector_factory(ref_collection)
                if not await ref_connector.exists("urn", urn):
                    raise HTTPException(422, dangling_reference_message(field, urn, ref_collection))
        connector = connector_factory(collection_name)
        try:
            doc = await connector.create(payload)
        except DuplicateError as exc:
            raise HTTPException(409, duplicate_message(collection_name)) from exc
        if log_audit:
            await write_audit_event(connector_factory, doc["urn"], "CREATED", list(payload.model_dump().keys()))
        if track_schema and doc.get("structure"):
            columns = doc["structure"]["columns"]
            summary = f"estrutura inicial ({len(columns)} coluna(s))"
            await write_schema_version(connector_factory, doc["urn"], doc["structure"], change_summary=summary)
        response.headers["Location"] = f"/{collection_name}/{doc['id']}"
        return doc

    @router.patch("/{item_id}", response_model=out_model)
    async def update(
        item_id: str, payload: update_model, connector_factory: ConnectorFactory = Depends(get_connector_factory)  # type: ignore[valid-type]
    ):
        connector = connector_factory(collection_name)
        old_doc = await connector.get(item_id)
        if not old_doc:
            raise HTTPException(404, not_found_message(collection_name, item_id))

        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            return old_doc

        merged_fields = merge_and_validate(old_doc, changes, out_model)
        doc = await connector.set_fields(item_id, merged_fields)
        changed_fields = list(changes.keys())
        if log_audit:
            await write_audit_event(connector_factory, doc["urn"], "UPDATED", changed_fields)
        if track_schema and "structure" in changed_fields:
            old_columns = (old_doc.get("structure") or {}).get("columns", [])
            new_columns = (doc.get("structure") or {}).get("columns", [])
            if old_columns != new_columns:
                summary = summarize_schema_change(old_columns, new_columns)
                await write_schema_version(connector_factory, doc["urn"], doc.get("structure"), change_summary=summary)
        return doc

    @router.delete("/{item_id}", status_code=204)
    async def delete(item_id: str, connector_factory: ConnectorFactory = Depends(get_connector_factory)):
        connector = connector_factory(collection_name)
        doc = await connector.get(item_id)
        if not doc:
            raise HTTPException(404, not_found_message(collection_name, item_id))
        if soft_delete:
            already_deleted = all(get_nested(doc, field) == value for field, value in soft_delete.items())
            if already_deleted:
                raise HTTPException(410, already_deleted_message(collection_name, doc["urn"]))
            await connector.set_fields(item_id, soft_delete)
        else:
            await connector.delete(item_id)
        if log_audit:
            await write_audit_event(connector_factory, doc["urn"], "DELETED", [])

    return router
