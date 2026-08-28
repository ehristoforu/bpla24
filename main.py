import asyncio
from contextlib import suppress
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram.types import BotCommand

from app.bot.handlers.main_router import BotRouter
from app.bot.keyboards.inline import get_user_actions_inline_keyboard
from app.config.settings import settings
from app.database.sqlite import SqliteDatabase
from app.ingestion.manager import IngestionManager
from app.nlp.processor import TextProcessor
from app.services.monitor_service import MonitorService


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="🚀 Запустить / Главное меню"),
        BotCommand(command="status", description="📊 Статус и текущие угрозы"),
        BotCommand(command="settings", description="⚙️ Настройки региона и режима"),
        BotCommand(command="safety", description="🚨 Памятка действий при угрозе"),
        BotCommand(command="legal", description="⚖️ Закон и ответственность"),
        BotCommand(command="github", description="💻 Исходный код на GitHub"),
        BotCommand(command="tunnel", description="🔒 Безопасный доступ к TG"),
        BotCommand(command="about", description="🛡 О проекте и создателях"),
        BotCommand(command="stop", description="🛑 Отключить оповещения"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if not settings.telegram_bot_token or settings.telegram_bot_token == "1234567890:replace_me":
        raise RuntimeError("Укажите валидный TELEGRAM_BOT_TOKEN в файле .env")

    db = SqliteDatabase(settings.db_path)
    await db.init()

    nlp = TextProcessor(settings.sources_path)
    ingestion = IngestionManager(nlp.create_notice)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    await setup_bot_commands(bot)

    monitor = MonitorService(
        bot=bot,
        db=db,
        nlp=nlp,
        ingestion=ingestion,
        actions_keyboard_factory=get_user_actions_inline_keyboard,
    )

    await monitor.refresh_sources()
    if settings.startup_prime_existing:
        await monitor.prime_existing_users()

    bot_router = BotRouter(db=db, nlp=nlp, monitor=monitor)
    dp = Dispatcher()
    dp.include_router(bot_router.router)

    monitor_task = asyncio.create_task(monitor.run_loop())

    logging.info("Бот БПЛА24 (@bpla24) успешно запущен.")
    try:
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        with suppress(asyncio.CancelledError):
            await monitor_task
        await bot.session.close()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
