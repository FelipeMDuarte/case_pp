import pytest
from httpx import AsyncClient
from pymongo.errors import PyMongoError

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_database_up(client: AsyncClient) -> None:
    response = await client.get("/health/database")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_database_down(client: AsyncClient) -> None:
    class BrokenAdmin:
        async def command(self, *args, **kwargs):
            raise PyMongoError("simulated failure")

    class BrokenClient:
        admin = BrokenAdmin()

    app.state.db_client = BrokenClient()

    response = await client.get("/health/database")

    assert response.status_code == 503
