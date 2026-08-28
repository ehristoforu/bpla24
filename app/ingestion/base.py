from abc import ABC, abstractmethod
import aiohttp
from app.models.schemas import Notice, SourceConfig


class ISourceFetcher(ABC):
    @abstractmethod
    async def fetch(self, session: aiohttp.ClientSession, source: SourceConfig) -> list[Notice]:
        pass
