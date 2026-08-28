import aiohttp
from app.config.settings import settings
from app.ingestion.base import ISourceFetcher
from app.ingestion.client import http_get_json
from app.models.schemas import DangerKind, Notice, SourceConfig


class RadarApiFetcher(ISourceFetcher):
    def __init__(self, factory_func) -> None:
        self.factory_func = factory_func

    async def fetch(self, session: aiohttp.ClientSession, source: SourceConfig) -> list[Notice]:
        data = await http_get_json(session, source.url)
        notices: list[Notice] = []

        history = data.get("history", [])
        if isinstance(history, list):
            for item in history[: settings.max_items_per_source]:
                text = item.get("text") or item.get("message") or item.get("description") or ""
                if not text:
                    continue

                title = item.get("title") or text[:120]
                published_at = item.get("date") or item.get("time") or item.get("createdAt")
                kind_raw = str(item.get("kind", "")).lower()

                notice = self.factory_func(
                    source=source,
                    title=title,
                    text=text,
                    url="https://radar-russia.ru/",
                    published_at=published_at,
                )
                if kind_raw in {"uav", "flamingo"}:
                    notice.kind = DangerKind.DRONE
                elif kind_raw in {"missile", "aviation_missile", "artillery"}:
                    notice.kind = DangerKind.ROCKET
                elif kind_raw in {"pvo", "pvo_prepare"}:
                    notice.kind = DangerKind.ALARM

                notices.append(notice)

        markers = data.get("markers", [])
        if isinstance(markers, list):
            for marker in markers[-settings.max_items_per_source:]:
                regions = marker.get("regions", [])
                districts = marker.get("districts", [])
                date = marker.get("date")
                kind_str = marker.get("kind", "")
                status = marker.get("status", "")

                loc_parts = []
                if isinstance(regions, list):
                    loc_parts.extend(regions)
                if isinstance(districts, list):
                    loc_parts.extend(districts)

                loc_str = ", ".join(loc_parts) if loc_parts else "Россия"
                text = f"Зафиксирована активность на карте: {loc_str}. Статус: {status}. Тип: {kind_str}"
                title = f"Радар: {kind_str.upper()} ({loc_str})"

                notice = self.factory_func(
                    source=source,
                    title=title,
                    text=text,
                    url="https://radar-russia.ru/",
                    published_at=date,
                )
                if kind_str in {"uav", "flamingo"}:
                    notice.kind = DangerKind.DRONE
                elif kind_str in {"missile", "aviation_missile"}:
                    notice.kind = DangerKind.ROCKET
                elif kind_str in {"pvo", "pvo_prepare"}:
                    notice.kind = DangerKind.ALARM

                notices.append(notice)

        return notices
