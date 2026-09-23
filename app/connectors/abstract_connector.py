from abc import ABC, abstractmethod

from pydantic import BaseModel


class DuplicateError(Exception):
    """Levantado quando uma escrita viola uma restrição de unicidade do connector."""
    # Necessário porque erros de duplicata são diferentes em bancos diferentes

class AbstractConnector(ABC):
    """Contrato que qualquer connector de persistência precisa cumprir (Mongo, Postgres, etc.)."""

    @abstractmethod
    async def create(self, payload: BaseModel) -> dict: ...

    @abstractmethod
    async def get(self, id: str) -> dict | None: ...

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100, filters: dict[str, str] | None = None) -> list[dict]: ...

    @abstractmethod
    async def count(self, filters: dict[str, str] | None = None) -> int: ...

    @abstractmethod
    async def set_fields(self, id: str, fields: dict) -> dict | None: ...

    @abstractmethod
    async def delete(self, id: str) -> bool: ...

    @abstractmethod
    async def exists(self, field: str, value: str) -> bool: ...
