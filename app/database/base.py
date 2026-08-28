from abc import ABC, abstractmethod
from app.models.schemas import Incident, ScopeType, Subscriber


class IDatabase(ABC):
    @abstractmethod
    async def init(self) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    @abstractmethod
    async def upsert_user(self, user_id: int, region: str, city: str) -> None:
        pass

    @abstractmethod
    async def get_user(self, user_id: int) -> Subscriber | None:
        pass

    @abstractmethod
    async def list_users(self) -> list[Subscriber]:
        pass

    @abstractmethod
    async def set_notify_scope(self, user_id: int, notify_scope: ScopeType) -> None:
        pass

    @abstractmethod
    async def deactivate_user(self, user_id: int) -> None:
        pass

    @abstractmethod
    async def was_sent(self, user_id: int, item_id: str) -> bool:
        pass

    @abstractmethod
    async def mark_incidents_sent(self, user_id: int, incidents: list[Incident]) -> None:
        pass

    @abstractmethod
    async def increment_stat(self, stat_name: str) -> None:
        pass

    @abstractmethod
    async def get_stats(self) -> dict[str, int]:
        pass

    @abstractmethod
    async def count_subscribers(self) -> tuple[int, int]:
        pass
