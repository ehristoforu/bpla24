from urllib.parse import urljoin
import aiohttp
from bs4 import BeautifulSoup

from app.config.settings import settings
from app.ingestion.base import ISourceFetcher
from app.ingestion.client import http_get_text
from app.models.schemas import Notice, SourceConfig


class HtmlFetcher(ISourceFetcher):
    def __init__(self, factory_func) -> None:
        self.factory_func = factory_func

    async def fetch(self, session: aiohttp.ClientSession, source: SourceConfig) -> list[Notice]:
        raw = await http_get_text(session, source.url)
        soup = BeautifulSoup(raw, "html.parser")
        notices: list[Notice] = []
        seen: set[str] = set()

        for link in soup.find_all("a", href=True):
            title = " ".join(link.get_text(" ", strip=True).split())
            if len(title) < 12:
                continue

            href = str(link.get("href", ""))
            if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue

            full_url = urljoin(source.url, href)
            if full_url in seen:
                continue
            seen.add(full_url)

            parent_text = " ".join(link.parent.get_text(" ", strip=True).split()) if link.parent else title
            notices.append(
                self.factory_func(
                    source=source,
                    title=title,
                    text=parent_text,
                    url=full_url,
                    published_at=None,
                )
            )
            if len(notices) >= settings.max_items_per_source:
                break
        return notices
