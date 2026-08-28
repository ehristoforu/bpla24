from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from app.config.settings import settings
from app.models.schemas import RegionConfig, ScopeType


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статус и угрозы"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🚨 Памятка действий"), KeyboardButton(text="⚖️ Закон и ответственность")],
            [KeyboardButton(text="💻 GitHub проекта"), KeyboardButton(text="🔒 Безопасный доступ к TG")],
            [KeyboardButton(text="🛡 О проекте")],
        ],
        resize_keyboard=True,
    )


def get_github_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Открыть репозиторий GitHub", url="https://github.com/ehristoforu/bpla24")]
        ]
    )


def get_tunnel_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Перейти", url="https://t.me/rostunnelbot")]
        ]
    )


def get_user_actions_inline_keyboard(notify_scope: ScopeType) -> InlineKeyboardMarkup:
    all_text = "✅ 🇷🇺 Вся Россия" if notify_scope == ScopeType.ALL else "🇷🇺 Вся Россия"
    region_text = "✅ 📍 Только мой регион" if notify_scope == ScopeType.REGION else "📍 Только мой регион"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=all_text, callback_data="notify:all")],
            [InlineKeyboardButton(text=region_text, callback_data="notify:region")],
            [InlineKeyboardButton(text="🔄 Сменить регион и город", callback_data="setup:start")],
            [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="status:refresh")],
        ]
    )


def get_regions_inline_keyboard(regions: list[RegionConfig], page: int = 0) -> InlineKeyboardMarkup:
    total = len(regions)
    per_page = settings.regions_per_page
    max_page = max((total - 1) // per_page, 0)
    page = max(0, min(page, max_page))
    start = page * per_page
    end = min(start + per_page, total)

    rows: list[list[InlineKeyboardButton]] = []
    for index in range(start, end):
        rows.append([InlineKeyboardButton(text=f"📍 {regions[index].name}", callback_data=f"r:set:{index}")])

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"r:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"Стр. {page + 1}/{max_page + 1}", callback_data="noop"))
    if page < max_page:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"r:page:{page + 1}"))

    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_cities_inline_keyboard(region: RegionConfig, region_index: int, page: int = 0) -> InlineKeyboardMarkup:
    cities = region.cities
    per_page = settings.cities_per_page
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🏢 Весь регион (все города)", callback_data=f"c:all:{region_index}")]
    ]

    if cities:
        max_page = max((len(cities) - 1) // per_page, 0)
        page = max(0, min(page, max_page))
        start = page * per_page
        end = min(start + per_page, len(cities))

        for index in range(start, end):
            rows.append([InlineKeyboardButton(text=cities[index].name, callback_data=f"c:set:{region_index}:{index}")])

        nav: list[InlineKeyboardButton] = []
        if page > 0:
            nav.append(InlineKeyboardButton(text="◀️", callback_data=f"c:page:{region_index}:{page - 1}"))
        nav.append(InlineKeyboardButton(text=f"{page + 1}/{max_page + 1}", callback_data="noop"))
        if page < max_page:
            nav.append(InlineKeyboardButton(text="▶️", callback_data=f"c:page:{region_index}:{page + 1}"))
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="✍️ Ввести город вручную", callback_data=f"c:manual:{region_index}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад к списку регионов", callback_data="r:page:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
