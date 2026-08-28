import asyncio
import logging
import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramAPIError
from aiogram.types import InlineKeyboardMarkup

from app.database.base import IDatabase
from app.models.schemas import Incident, ScopeType, Subscriber
from app.services.formatter_service import FormatterService


class BroadcastQueue:
    def __init__(self, bot: Bot, db: IDatabase, max_concurrent: int = 25) -> None:
        self.bot = bot
        self.db = db
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _send_one(
        self,
        subscriber: Subscriber,
        incidents: list[Incident],
        keyboard: InlineKeyboardMarkup | None,
    ) -> None:
        async with self.semaphore:
            if not incidents:
                return

            visible = incidents[:5]
            hidden = max(0, len(incidents) - len(visible))
            text = FormatterService.build_digest(
                scope=subscriber.notify_scope,
                region=subscriber.region,
                city=subscriber.city,
                incidents=visible,
                hidden_count=hidden,
            )

            try:
                await self.bot.send_message(
                    chat_id=subscriber.user_id,
                    text=text,
                    reply_markup=keyboard,
                )
                await self.db.mark_incidents_sent(subscriber.user_id, incidents)
            except TelegramForbiddenError:
                await self.db.deactivate_user(subscriber.user_id)
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 1)
                try:
                    await self.bot.send_message(
                        chat_id=subscriber.user_id,
                        text=text,
                        reply_markup=keyboard,
                    )
                    await self.db.mark_incidents_sent(subscriber.user_id, incidents)
                except Exception:
                    pass
            except TelegramAPIError as exc:
                logging.warning("Ошибка отправки пользователю %s: %s", subscriber.user_id, exc)

    async def broadcast(
        self,
        tasks: list[tuple[Subscriber, list[Incident], InlineKeyboardMarkup | None]],
    ) -> None:
        if not tasks:
            return
        coros = [self._send_one(sub, incs, kb) for sub, incs, kb in tasks]
        await asyncio.gather(*coros, return_exceptions=True)
