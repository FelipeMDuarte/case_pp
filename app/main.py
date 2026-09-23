from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from app.api.routers import all_routers
from app.config import get_settings

settings = get_settings()


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
    except PyMongoError:
        raise HTTPException(503, "Database is not reachable.")
    return {"status": "ok"}
