from contextlib import asynccontextmanager

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import get_settings
from app.api.routers import all_routers

settings = get_settings()


@asynccontextmanager
async def start_mongo(app: FastAPI):
    app.state.db_client = AsyncIOMotorClient(settings.mongo_uri)
    yield
    app.state.db_client.close()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=start_mongo)

for router in all_routers:
    app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
