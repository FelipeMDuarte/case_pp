from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.config import get_settings
from app.main import app, making_indexes_unique


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    # podia usar dependency_overrides
    db_client = AsyncMongoMockClient()
    app.state.db_client = db_client
    # mesmos índices únicos do lifespan real, senão os testes de duplicata não reproduziriam
    # o comportamento de produção (mongomock só recusa duplicata se o índice existir de verdade)
    await making_indexes_unique(db_client[get_settings().mongo_db])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
