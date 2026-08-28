from html import escape
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models.schemas import DangerKind, Incident, Notice, ScopeType

try:
    LOCAL_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    LOCAL_TZ = timezone.utc


class FormatterService:
    @staticmethod
    def format_time(value: str | None) -> str:
        if not value:
            return "время не указано"
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M")
        except Exception:
            return value

    @staticmethod
    def get_kind_emoji(kind: DangerKind) -> str:
        mapping = {
            DangerKind.DRONE: "🛩 <b>УГРОЗА БПЛА / ДРОНОВ</b>",
            DangerKind.ROCKET: "🚀 <b>РАКЕТНАЯ ОПАСНОСТЬ</b>",
            DangerKind.ALARM: "🚨 <b>РЕЖИМ ТРЕВОГИ / ОПАСНОСТЬ</b>",
            DangerKind.CLEAR: "🟢 <b>ОТБОЙ ОПАСНОСТИ / ТРЕВОГИ</b>",
            DangerKind.OTHER: "ℹ️ <b>ОПОВЕЩЕНИЕ</b>",
        }
        return mapping.get(kind, "⚠️ <b>ВНИМАНИЕ</b>")

    @staticmethod
    def format_incident(incident: Incident, index: int | None = None) -> str:
        locs = [l for l in incident.locations if l.lower() not in {"россия", "рф", "вся россия"}]
        loc_str = ", ".join(locs[:6]) if locs else "Россия"
        if len(locs) > 6:
            loc_str += f" и еще {len(locs) - 6}"

        best_notice = max(incident.notices, key=lambda n: len(n.text))
        visible_text = best_notice.text or best_notice.title

        lines = []
        header = f"{index}. {FormatterService.get_kind_emoji(incident.kind)}" if index else FormatterService.get_kind_emoji(incident.kind)
        lines.append(header)
        lines.append(f"📍 Локация: <b>{escape(loc_str)}</b>")
        pub_time = max((n.published_at or "" for n in incident.notices), default="")
        lines.append(f"🕒 Время: <code>{escape(FormatterService.format_time(pub_time or None))}</code>")
        lines.append("")
        lines.append(f"<blockquote>{escape(visible_text[:600]) + ('…' if len(visible_text) > 600 else '')}</blockquote>")
        return "\n".join(lines)

    @staticmethod
    def build_digest(
        scope: ScopeType,
        region: str,
        city: str,
        incidents: list[Incident],
        hidden_count: int = 0,
    ) -> str:
        scope_name = "Вся Россия 🇷🇺" if scope == ScopeType.ALL else f"{region} ({city or 'весь регион'})"
        lines = [
            "🛰 <b>БПЛА24 | Мониторинг угроз РФ</b>",
            f"🎯 Зона оповещения: <b>{escape(scope_name)}</b>",
            "───────────────────",
        ]

        for i, inc in enumerate(incidents, 1):
            lines.append("")
            lines.append(FormatterService.format_incident(inc, i))

        if hidden_count > 0:
            lines.append("")
            lines.append(f"<i>(И еще {hidden_count} событий скрыто для защиты от спама)</i>")

        lines.append("")
        lines.append("⚠️ <i>Соблюдайте спокойствие и правила безопасности. Не снимайте работу ПВО!</i>")
        return "\n".join(lines).strip()

    @staticmethod
    def build_status(
        scope: ScopeType,
        region: str,
        city: str,
        incidents: list[Incident],
        updated_at: datetime | None,
    ) -> str:
        scope_name = "Вся Россия 🇷🇺" if scope == ScopeType.ALL else f"{region} ({city or 'весь регион'})"
        lines = [
            "📊 <b>Текущий статус мониторинга БПЛА24</b>",
            f"📍 Ваш регион: <b>{escape(region)}</b>" + (f", г. <b>{escape(city)}</b>" if city else ""),
            f"🔔 Режим уведомлений: <b>{escape(scope_name)}</b>",
            "───────────────────",
        ]

        if incidents:
            lines.append("⚡️ <b>Последние зафиксированные события:</b>")
            for i, inc in enumerate(incidents[:5], 1):
                lines.append("")
                lines.append(FormatterService.format_incident(inc, i))
        else:
            lines.append("✅ <b>Активных угроз и новых сообщений по вашему фильтру не обнаружено.</b>")

        if updated_at:
            lines.append("")
            lines.append(f"⏱ <i>Обновлено: {updated_at.astimezone(LOCAL_TZ).strftime('%d.%m.%Y %H:%M:%S')} (МСК)</i>")

        return "\n".join(lines).strip()
