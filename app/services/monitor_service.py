import asyncio
import logging
from datetime import datetime, timezone
import aiohttp
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from app.config.settings import settings
from app.database.base import IDatabase
from app.ingestion.manager import IngestionManager
from app.models.schemas import DangerKind, Incident, Notice, ScopeType, SourceConfig, SourceKind, Subscriber
from app.nlp.processor import TextProcessor
from app.services.broadcast_service import BroadcastQueue


class MonitorService:
    def __init__(
        self,
        bot: Bot,
        db: IDatabase,
        nlp: TextProcessor,
        ingestion: IngestionManager,
        actions_keyboard_factory,
    ) -> None:
        self.bot = bot
        self.db = db
        self.nlp = nlp
        self.ingestion = ingestion
        self.actions_keyboard_factory = actions_keyboard_factory
        self.broadcaster = BroadcastQueue(bot, db)

        self._cached_notices: list[Notice] = []
        self._last_update: datetime | None = None
        self._lock = asyncio.Lock()

    def _get_all_sources(self) -> list[SourceConfig]:
        sources: list[SourceConfig] = list(self.nlp.global_sources)
        for reg in self.nlp.regions:
            sources.extend(reg.sources)

        if settings.enable_radar_api and settings.radar_api_url:
            sources.append(
                SourceConfig(
                    name="Radar Russia API (Live)",
                    kind=SourceKind.RADAR_API,
                    url=settings.radar_api_url,
                    locations=["Россия"],
                )
            )
        return sources

    async def refresh_sources(self) -> list[Notice]:
        all_sources = self._get_all_sources()
        collected_notices: list[Notice] = []

        async with aiohttp.ClientSession() as session:
            tasks = [self.ingestion.fetch_source(session, src) for src in all_sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for src, res in zip(all_sources, results):
            if isinstance(res, Exception):
                logging.debug("Ошибка получения источника %s: %s", src.name, res)
                continue
            for n in res:
                if n.kind != DangerKind.OTHER and not self.nlp.is_ignored(f"{n.title} {n.text}"):
                    collected_notices.append(n)

        async with self._lock:
            self._cached_notices = collected_notices
            self._last_update = datetime.now(timezone.utc)

        return collected_notices

    def filter_notices_for_user(self, subscriber: Subscriber, notices: list[Notice]) -> list[Notice]:
        if subscriber.notify_scope == ScopeType.ALL:
            return notices

        matched = []
        for n in notices:
            if self.nlp.is_relevant_for_region(n, subscriber.region, subscriber.city):
                matched.append(n)

        return matched

    async def get_current_incidents_for_user(self, subscriber: Subscriber) -> tuple[list[Incident], datetime | None]:
        async with self._lock:
            cached = list(self._cached_notices)
            last_up = self._last_update

        filtered = self.filter_notices_for_user(subscriber, cached)
        incidents = self.nlp.group_into_incidents(filtered)
        return incidents, last_up

    async def prime_existing_users(self) -> None:
        async with self._lock:
            cached = list(self._cached_notices)
        users = await self.db.list_users()
        for user in users:
            filtered = self.filter_notices_for_user(user, cached)
            incidents = self.nlp.group_into_incidents(filtered)
            await self.db.mark_incidents_sent(user.user_id, incidents)

    async def check_and_notify(self) -> None:
        async with self._lock:
            cached = list(self._cached_notices)

        users = await self.db.list_users()
        broadcast_tasks: list[tuple[Subscriber, list[Incident], InlineKeyboardMarkup | None]] = []

        for user in users:
            filtered = self.filter_notices_for_user(user, cached)
            incidents = self.nlp.group_into_incidents(filtered)
            new_incidents: list[Incident] = []

            for inc in incidents:
                was_sent = await self.db.was_sent(user.user_id, f"event:{inc.key}")
                if not was_sent:
                    new_incidents.append(inc)

            if new_incidents:
                kb = self.actions_keyboard_factory(user.notify_scope)
                broadcast_tasks.append((user, new_incidents, kb))

        if broadcast_tasks:
            await self.broadcaster.broadcast(broadcast_tasks)

    async def run_loop(self) -> None:
        while True:
            try:
                await self.refresh_sources()
                await self.check_and_notify()
            except Exception:
                logging.exception("Ошибка в цикле мониторинга")
            await asyncio.sleep(max(settings.poll_interval_seconds, 30))
