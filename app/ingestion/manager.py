import aiohttp
from app.ingestion.base import ISourceFetcher
from app.ingestion.html import HtmlFetcher
from app.ingestion.radar_api import RadarApiFetcher
from app.ingestion.rss import RssFetcher
from app.ingestion.telegram import TelegramFetcher
from app.models.schemas import Notice, SourceConfig, SourceKind


class IngestionManager:
    def __init__(self, factory_func) -> None:
        self.fetchers: dict[SourceKind, ISourceFetcher] = {
            SourceKind.TELEGRAM: TelegramFetcher(factory_func),
            SourceKind.RSS: RssFetcher(factory_func),
            SourceKind.HTML: HtmlFetcher(factory_func),
            SourceKind.RADAR_API: RadarApiFetcher(factory_func),
        }

    async def fetch_source(self, session: aiohttp.ClientSession, source: SourceConfig) -> list[Notice]:
        fetcher = self.fetchers.get(source.kind)
        if not fetcher:
            raise ValueError(f"Неизвестный тип источника: {source.kind}")
        return await fetcher.fetch(session, source)
