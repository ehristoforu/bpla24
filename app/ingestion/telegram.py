import aiohttp
from bs4 import BeautifulSoup

from app.config.settings import settings
from app.ingestion.base import ISourceFetcher
from app.ingestion.client import http_get_text
from app.models.schemas import Notice, SourceConfig


class TelegramFetcher(ISourceFetcher):
    def __init__(self, factory_func) -> None:
        self.factory_func = factory_func

    async def fetch(self, session: aiohttp.ClientSession, source: SourceConfig) -> list[Notice]:
        url = source.url
        if source.channel:
            url = f"https://t.me/s/{source.channel.lstrip('@')}"

        raw = await http_get_text(session, url)
        soup = BeautifulSoup(raw, "html.parser")
        notices: list[Notice] = []
        messages = soup.select(".tgme_widget_message")

        for message in messages[-settings.max_items_per_source:]:
            text_node = message.select_one(".tgme_widget_message_text")
            if not text_node:
                continue
            text = " ".join(text_node.get_text(" ", strip=True).split())
            if not text:
                continue

            title = text[:140]
            link_node = message.select_one("a.tgme_widget_message_date")
            link = link_node.get("href", source.url) if link_node else source.url
            time_node = message.select_one("time")
            published = time_node.get("datetime") if time_node else None

            notices.append(
                self.factory_func(
                    source=source,
                    title=title,
                    text=text,
                    url=str(link),
                    published_at=published,
                )
            )
        return notices
