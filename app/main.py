from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.api.routers import all_routers
from app.api.utils import validation_error_message
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import log_requests

settings = get_settings()
configure_logging(settings.debug)


@asynccontextmanager
async def start_mongo(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongo_uri, tz_aware=True)
    app.state.db_client = client
    await making_indexes_unique(client[settings.mongo_db])
    yield
    client.close()

# Garantir que não tenhamos nem urn nem relação de fluxo de dados duplicados
async def making_indexes_unique(database) -> None:
    await database["metadata"].create_index("urn", unique=True)
    await database["data_flows"].create_index([("source_urn", 1), ("target_urn", 1)], unique=True)


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=start_mongo)

# Normalizando erro de 422 do pydantic com os custom error
@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": validation_error_message(exc.errors())})

# Configurações de logger http
app.middleware("http")(log_requests)

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
