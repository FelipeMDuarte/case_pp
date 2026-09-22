from collections.abc import Callable

from fastapi import Request

from app.config import get_settings
from app.connectors.abstract_connector import AbstractConnector
from app.connectors.mongo_con import MongoConnector

ConnectorFactory = Callable[[str], AbstractConnector]

def get_connector_factory(request: Request) -> ConnectorFactory:
    settings = get_settings()
    database = request.app.state.db_client[settings.mongo_db]

    def factory(collection_name: str) -> AbstractConnector:
        return MongoConnector(database, collection_name)

    return factory
