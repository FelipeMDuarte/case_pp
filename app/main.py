import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.api.routers import all_routers
from app.api.utils import validation_error_message
from app.config import get_settings
from app.logging_config import configure_logging, request_id_ctx

settings = get_settings()
configure_logging(settings.debug)
logger = logging.getLogger("case_pp")


@asynccontextmanager
async def start_mongo(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_uri)
    app.state.db_client = client
    await making_indexes_unique(client[settings.mongo_db])
    yield
    client.close()

# Garantir que não tenhamos nem urn nem relação de fluxo de dados duplicados
async def making_indexes_unique(database) -> None:
    await database["metadata"].create_index("urn", unique=True)
    await database["data_flows"].create_index([("source_urn", 1), ("target_urn", 1)], unique=True)


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=start_mongo)

# Normalizando erro de 422 do pydantic com dos custom
@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": validation_error_message(exc.errors())})


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    token = request_id_ctx.set(request_id)
    start = time.perf_counter()
    try:
        logger.info("%s %s - started", request.method, request.url.path)
        response = await call_next(request)
    except Exception:
        logger.exception("%s %s - unhandled error", request.method, request.url.path)
        raise
    else:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s - %s (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)


# Incluindo rotas da API
for router in all_routers:
    app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/database")
async def health_database():
    try:
        await app.state.db_client.admin.command("ping")
    except PyMongoError as exc:
        raise HTTPException(503, "Database is not reachable.") from exc
    return {"status": "ok"}
