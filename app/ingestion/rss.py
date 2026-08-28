import aiohttp
import feedparser

from app.config.settings import settings
from app.ingestion.base import ISourceFetcher
from app.ingestion.client import http_get_text
from app.models.schemas import Notice, SourceConfig


class RssFetcher(ISourceFetcher):
    def __init__(self, factory_func) -> None:
        self.factory_func = factory_func

    async def fetch(self, session: aiohttp.ClientSession, source: SourceConfig) -> list[Notice]:
        raw = await http_get_text(session, source.url)
        parsed = feedparser.parse(raw)
        notices: list[Notice] = []

        for entry in parsed.entries[: settings.max_items_per_source]:
            title = " ".join(getattr(entry, "title", "").split()).strip()
            summary = " ".join(getattr(entry, "summary", "").split()).strip()
            link = " ".join(getattr(entry, "link", source.url).split()).strip()
            published = getattr(entry, "published", "") or getattr(entry, "updated", "") or None

            if title or summary:
                notices.append(
                    self.factory_func(
                        source=source,
                        title=title,
                        text=summary,
                        url=link,
                        published_at=published,
                    )
                )
        return notices
