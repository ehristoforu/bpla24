import asyncio
from contextlib import suppress
from html import escape
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.inline import (
    get_cities_inline_keyboard,
    get_github_inline_keyboard,
    get_main_reply_keyboard,
    get_regions_inline_keyboard,
    get_tunnel_inline_keyboard,
    get_user_actions_inline_keyboard,
)
from app.bot.states import SetupState
from app.config.settings import settings
from app.database.base import IDatabase
from app.models.schemas import ScopeType
from app.nlp.processor import TextProcessor
from app.services.formatter_service import FormatterService
from app.services.info_service import InfoService
from app.services.monitor_service import MonitorService


class BotRouter:
    def __init__(self, db: IDatabase, nlp: TextProcessor, monitor: MonitorService) -> None:
        self.db = db
        self.nlp = nlp
        self.monitor = monitor
        self.router = Router()
        self._register_routes()

    def _is_admin(self, user_id: int) -> bool:
        raw_admins = [x.strip() for x in settings.admin_ids.split(",") if x.strip()]
        return str(user_id) in raw_admins

    async def _send_status_screen(
        self,
        bot: Bot,
        chat_id: int,
        user_id: int,
        edit_message_id: int | None = None,
    ) -> None:
        await self.db.increment_stat("status_views")
        user = await self.db.get_user(user_id)
        if not user:
            if edit_message_id:
                try:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=edit_message_id,
                        text="👋 <b>Добро пожаловать в БПЛА24!</b>\n\nДля начала работы выберите ваш регион:",
                        reply_markup=get_regions_inline_keyboard(self.nlp.regions, 0),
                    )
                    return
                except Exception as exc:
                    logging.debug("Ошибка редактирования сообщения: %s", exc)
            await bot.send_message(
                chat_id=chat_id,
                text="👋 <b>Добро пожаловать в БПЛА24!</b>\n\nДля начала работы выберите ваш регион:",
                reply_markup=get_regions_inline_keyboard(self.nlp.regions, 0),
            )
            return

        incidents, updated_at = await self.monitor.get_current_incidents_for_user(user)
        text = FormatterService.build_status(
            scope=user.notify_scope,
            region=user.region,
            city=user.city,
            incidents=incidents,
            updated_at=updated_at,
        )
        if edit_message_id:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=edit_message_id,
                    text=text,
                    reply_markup=get_user_actions_inline_keyboard(user.notify_scope),
                )
                return
            except Exception as exc:
                logging.debug("Ошибка редактирования сообщения: %s", exc)

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=get_user_actions_inline_keyboard(user.notify_scope),
        )

    def _register_routes(self) -> None:
        r = self.router

        @r.message(CommandStart())
        async def cmd_start(message: Message, state: FSMContext) -> None:
            await state.clear()
            if message.from_user:
                user = await self.db.get_user(message.from_user.id)
                if user:
                    await message.answer("👋 С возвращением в <b>БПЛА24</b>!", reply_markup=get_main_reply_keyboard())
                    assert message.bot is not None
                    await self._send_status_screen(message.bot, message.chat.id, message.from_user.id)
                    return
            await message.answer(
                "🇷🇺 <b>БПЛА24 (@bpla24)</b> — система мониторинга воздушных и ракетных угроз РФ.\n\n"
                "Пожалуйста, выберите ваш регион:",
                reply_markup=get_regions_inline_keyboard(self.nlp.regions, 0),
            )
            await state.set_state(SetupState.region)

        @r.message(Command("status"))
        @r.message(F.text == "📊 Статус и угрозы")
        async def cmd_status(message: Message) -> None:
            if not message.from_user or not message.bot:
                return
            await self._send_status_screen(
                message.bot,
                message.chat.id,
                message.from_user.id,
            )

        @r.message(Command("settings"))
        @r.message(F.text == "⚙️ Настройки")
        async def cmd_settings(message: Message) -> None:
            if message.from_user and message.bot:
                user = await self.db.get_user(message.from_user.id)
                if user:
                    text = (
                        f"⚙️ <b>Настройки оповещений</b>\n\n"
                        f"📍 Регион: <b>{user.region}</b>\n"
                        f"🏢 Город: <b>{user.city or 'Все города региона'}</b>\n"
                        f"🔔 Режим: <b>{'Вся Россия' if user.notify_scope == ScopeType.ALL else 'Только мой регион'}</b>"
                    )
                    await message.answer(text, reply_markup=get_user_actions_inline_keyboard(user.notify_scope))
                else:
                    await self._send_status_screen(message.bot, message.chat.id, message.from_user.id)

        @r.message(Command("github"))
        @r.message(F.text == "💻 GitHub проекта")
        async def cmd_github(message: Message) -> None:
            await message.answer(
                "💻 <b>Исходный код проекта БПЛА24</b> доступен на GitHub под свободной лицензией GPL-3.0.\n\n"
                "Вы можете ознакомиться с кодом, предложить улучшения или развернуть собственного бота.",
                reply_markup=get_github_inline_keyboard(),
            )

        @r.message(Command("tunnel"))
        @r.message(F.text == "🔒 Безопасный доступ к TG")
        async def cmd_tunnel(message: Message) -> None:
            await message.answer(
                "🔒 <b>Безопасный доступ к Telegram</b>\n\n"
                "Для бесперебойного получения экстренных оповещений "
                "используйте инструмент ниже (не реклама!).",
                reply_markup=get_tunnel_inline_keyboard(),
            )

        @r.message(Command("safety"))
        @r.message(F.text == "🚨 Памятка действий")
        async def cmd_safety(message: Message) -> None:
            await message.answer(InfoService.get_safety_guide())

        @r.message(Command("legal"))
        @r.message(F.text == "⚖️ Закон и ответственность")
        async def cmd_legal(message: Message) -> None:
            await message.answer(InfoService.get_legal_disclaimer())

        @r.message(Command("about"))
        @r.message(F.text == "🛡 О проекте")
        async def cmd_about(message: Message) -> None:
            await message.answer(InfoService.get_about())

        @r.message(Command("admin"))
        async def cmd_admin(message: Message) -> None:
            if not message.from_user or not self._is_admin(message.from_user.id):
                return
            stats = await self.db.get_stats()
            total_users, active_users = await self.db.count_subscribers()
            status_views = stats.get("status_views", 0)

            text = (
                "👑 <b>Панель администратора БПЛА24</b>\n"
                "───────────────────\n"
                f"👥 <b>Всего зарегистрировано пользователей:</b> <code>{total_users}</code>\n"
                f"🟢 <b>Активных подписчиков:</b> <code>{active_users}</code>\n"
                f"🔴 <b>Отключили уведомления:</b> <code>{total_users - active_users}</code>\n"
                f"📊 <b>Всего просмотров/обновлений статуса:</b> <code>{status_views}</code>\n"
                "───────────────────\n"
                f"⚙️ <b>Подключено регионов РФ:</b> <code>{len(self.nlp.regions)}</code>\n"
                f"🛰 <b>Radar Russia API:</b> <code>{'Включен' if settings.enable_radar_api else 'Отключен'}</code>\n"
                f"⏱ <b>Интервал опроса:</b> <code>{settings.poll_interval_seconds} сек</code>"
            )
            await message.answer(text)

        @r.message(Command("stop"))
        async def cmd_stop(message: Message, state: FSMContext) -> None:
            if message.from_user:
                await self.db.deactivate_user(message.from_user.id)
            await state.clear()
            await message.answer("🛑 <b>Уведомления отключены.</b> Для повторной активации нажмите /start.")

        @r.callback_query(F.data == "noop")
        async def cb_noop(callback: CallbackQuery) -> None:
            await callback.answer()

        @r.callback_query(F.data.startswith("notify:"))
        async def cb_notify_scope(callback: CallbackQuery) -> None:
            if not callback.from_user or not callback.message:
                return
            scope_val = callback.data.split(":", 1)[1]
            scope = ScopeType.REGION if scope_val == "region" else ScopeType.ALL
            await self.db.set_notify_scope(callback.from_user.id, scope)
            with suppress(Exception):
                await callback.answer("✅ Режим оповещений обновлен")
            assert callback.bot is not None
            await self._send_status_screen(
                callback.bot,
                callback.message.chat.id,
                callback.from_user.id,
                edit_message_id=callback.message.message_id,
            )

        @r.callback_query(F.data == "status:refresh")
        async def cb_refresh_status(callback: CallbackQuery) -> None:
            if not callback.from_user or not callback.message or not callback.bot:
                return
            with suppress(Exception):
                await callback.answer("🔄 Обновление статуса...")

            # Немедленно показываем пользователю индикацию загрузки
            with suppress(Exception):
                await callback.message.edit_text("⏳ <i>Обновление данных из оперативных источников...</i>")

            # Запускаем фоновое обновление источников не блокируя поток
            asyncio.create_task(self.monitor.refresh_sources())

            # Ждем короткую паузу и показываем актуальное состояние из кэша
            await asyncio.sleep(0.5)
            await self._send_status_screen(
                callback.bot,
                callback.message.chat.id,
                callback.from_user.id,
                edit_message_id=callback.message.message_id,
            )

        @r.callback_query(F.data == "setup:start")
        async def cb_setup_start(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.message:
                return
            await state.clear()
            await callback.answer()
            await callback.message.edit_text(
                "📍 Выберите ваш регион:",
                reply_markup=get_regions_inline_keyboard(self.nlp.regions, 0),
            )
            await state.set_state(SetupState.region)

        @r.callback_query(F.data.startswith("r:page:"))
        async def cb_region_page(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.message:
                return
            page = int(callback.data.split(":")[2])
            await callback.answer()
            await callback.message.edit_text(
                "📍 Выберите ваш регион:",
                reply_markup=get_regions_inline_keyboard(self.nlp.regions, page),
            )
            await state.set_state(SetupState.region)

        @r.callback_query(F.data.startswith("r:set:"))
        async def cb_region_set(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.message:
                return
            reg_idx = int(callback.data.split(":")[2])
            reg = self.nlp.regions[reg_idx]
            await state.update_data(region=reg.name, region_idx=reg_idx)
            await state.set_state(SetupState.city)
            await callback.answer()
            await callback.message.edit_text(
                f"🏢 Выберите город для региона: <b>{escape(reg.name)}</b>",
                reply_markup=get_cities_inline_keyboard(reg, reg_idx, 0),
            )

        @r.callback_query(F.data.startswith("c:page:"))
        async def cb_city_page(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.message:
                return
            parts = callback.data.split(":")
            reg_idx, page = int(parts[2]), int(parts[3])
            reg = self.nlp.regions[reg_idx]
            await callback.answer()
            await callback.message.edit_text(
                f"🏢 Выберите город для региона: <b>{escape(reg.name)}</b>",
                reply_markup=get_cities_inline_keyboard(reg, reg_idx, page),
            )

        @r.callback_query(F.data.startswith("c:all:"))
        async def cb_city_all(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.from_user or not callback.message or not callback.bot:
                return
            reg_idx = int(callback.data.split(":")[2])
            reg = self.nlp.regions[reg_idx]
            await self.db.upsert_user(callback.from_user.id, reg.name, "")
            await state.clear()
            with suppress(Exception):
                await callback.answer("✅ Настройки сохранены!")
            await callback.message.answer("🎉 Вы успешно подписались на оповещения!", reply_markup=get_main_reply_keyboard())
            await self._send_status_screen(callback.bot, callback.message.chat.id, callback.from_user.id)

        @r.callback_query(F.data.startswith("c:set:"))
        async def cb_city_set(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.from_user or not callback.message or not callback.bot:
                return
            parts = callback.data.split(":")
            reg_idx, city_idx = int(parts[2]), int(parts[3])
            reg = self.nlp.regions[reg_idx]
            city_name = reg.cities[city_idx].name
            await self.db.upsert_user(callback.from_user.id, reg.name, city_name)
            await state.clear()
            with suppress(Exception):
                await callback.answer("✅ Настройки сохранены!")
            await callback.message.answer("🎉 Вы успешно подписались на оповещения!", reply_markup=get_main_reply_keyboard())
            await self._send_status_screen(callback.bot, callback.message.chat.id, callback.from_user.id)

        @r.callback_query(F.data.startswith("c:manual:"))
        async def cb_city_manual(callback: CallbackQuery, state: FSMContext) -> None:
            if not callback.message:
                return
            reg_idx = int(callback.data.split(":")[2])
            reg = self.nlp.regions[reg_idx]
            await state.update_data(region=reg.name)
            await state.set_state(SetupState.city)
            await callback.answer()
            await callback.message.answer("✍️ Пожалуйста, напишите название вашего города в чат:")

        @r.message(SetupState.region)
        async def msg_setup_region(message: Message, state: FSMContext) -> None:
            text = self.nlp.compact(message.text or "")
            for i, reg in enumerate(self.nlp.regions):
                if any(self.nlp.rough_phrase_match(text, x) for x in [reg.name, *reg.aliases]):
                    await state.update_data(region=reg.name, region_idx=i)
                    await state.set_state(SetupState.city)
                    await message.answer(
                        f"🏢 Выберите город для региона: <b>{escape(reg.name)}</b>",
                        reply_markup=get_cities_inline_keyboard(reg, i, 0),
                    )
                    return
            await message.answer(
                "❌ Регион не распознан. Пожалуйста, выберите кнопку из списка:",
                reply_markup=get_regions_inline_keyboard(self.nlp.regions, 0),
            )

        @r.message(SetupState.city)
        async def msg_setup_city(message: Message, state: FSMContext) -> None:
            if not message.from_user or not message.bot:
                return
            data = await state.get_data()
            region_name = data.get("region")
            if not region_name:
                await state.clear()
                await message.answer("Ошибка состояния. Введите /start заново.")
                return

            raw_city = self.nlp.compact(message.text or "")
            city_val = raw_city if raw_city.lower() not in {"-", "нет", "любой", "все"} else ""
            await self.db.upsert_user(message.from_user.id, region_name, city_val)
            await state.clear()
            await message.answer("🎉 Настройки успешно сохранены!", reply_markup=get_main_reply_keyboard())
            await self._send_status_screen(message.bot, message.chat.id, message.from_user.id)
