import hashlib
import json
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.models.schemas import CityConfig, DangerKind, Incident, Notice, RegionConfig, SourceConfig

try:
    LOCAL_TZ = ZoneInfo("Europe/Moscow")
except Exception:
    LOCAL_TZ = timezone.utc

DRONE_TERMS = [
    "бпла",
    "беспилотник",
    "беспилотники",
    "беспилотный",
    "беспилотные",
    "дрон",
    "дроны",
    "атака дронов",
    "атака беспилотников",
    "атака бпла",
    "угроза атаки бпла",
    "опасность атаки бпла",
    "беспилотная опасность",
    "обнаружен бпла",
    "обнаружены бпла",
    "сбит бпла",
    "сбиты бпла",
    "уничтожен бпла",
    "уничтожены бпла",
    "перехвачен бпла",
    "перехвачены бпла",
    "беспилотных летательных аппаратов",
    "беспилотный летательный аппарат",
]

ROCKET_TERMS = [
    "ракета",
    "ракеты",
    "ракетная опасность",
    "ракетная угроза",
    "ракетная атака",
    "угроза ракетной атаки",
    "ракетный удар",
    "баллистическая угроза",
]

ALARM_TERMS = [
    "красный уровень",
    "красного уровня",
    "желтый уровень",
    "желтого уровня",
    "жёлтый уровень",
    "жёлтого уровня",
    "воздушная опасность",
    "воздушной опасности",
    "режим тревоги",
    "режим опасности",
    "сигнал тревоги",
    "угроза атаки",
    "опасность атаки",
    "сирена",
    "внимание всем",
]

CLEAR_TERMS = [
    "отбой",
    "отбой красного уровня",
    "отбой желтого уровня",
    "отбой жёлтого уровня",
    "угроза атаки бпла отменена",
    "опасность атаки бпла отменена",
    "воздушная опасность отменена",
    "ракетная опасность отменена",
    "угроза снята",
    "опасность снята",
    "отменена тревога",
    "цель признана ложной",
]

WEATHER_TERMS = [
    "неблагоприятных метеорологических",
    "неблагоприятные метеорологические",
    "метеорологических явлений",
    "метеорологические явления",
    "штормовое предупреждение",
    "гроза",
    "грозой",
    "дожд",
    "ливень",
    "ливни",
    "ветер",
    "ветра",
    "порывы ветра",
    "снег",
    "метель",
    "туман",
    "гололед",
    "гололёд",
    "град",
    "жара",
    "заморозки",
    "шквал",
    "паводок",
]

AVIATION_ONLY_TERMS = [
    "введены временные ограничения",
    "сняты временные ограничения",
    "ограничения на прием",
    "ограничения на приём",
    "ограничения на выпуск",
    "аэропорт",
    "аэропорты",
    "план ковер",
    "план ковёр",
]


class TextProcessor:
    def __init__(self, sources_path: str) -> None:
        self.sources_path = sources_path
        self.regions: list[RegionConfig] = []
        self.ignore_keywords: list[str] = []
        self.global_sources: list[SourceConfig] = []
        self._load_sources()

    def _load_sources(self) -> None:
        with open(self.sources_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.ignore_keywords = [str(x).lower() for x in data.get("ignore_keywords", [])]
        self.global_sources = [
            SourceConfig(
                name=item["name"],
                kind=item["kind"],
                url=item["url"],
                locations=item.get("locations", []),
                channel=item.get("channel", ""),
            )
            for item in data.get("global_sources", [])
        ]

        self.regions = []
        for reg in data.get("regions", []):
            cities = [
                CityConfig(name=c["name"], aliases=c.get("aliases", []))
                for c in reg.get("cities", [])
            ]
            sources = [
                SourceConfig(
                    name=s["name"],
                    kind=s["kind"],
                    url=s["url"],
                    locations=s.get("locations", []),
                    channel=s.get("channel", ""),
                )
                for s in reg.get("sources", [])
            ]
            self.regions.append(
                RegionConfig(
                    name=reg["name"],
                    aliases=reg.get("aliases", []),
                    cities=cities,
                    sources=sources,
                )
            )

    @staticmethod
    def normalize(text: str) -> str:
        text = text.replace("ё", "е")
        text = re.sub(r"[^a-zа-я0-9]+", " ", text.lower(), flags=re.IGNORECASE)
        return " ".join(text.split())

    @staticmethod
    def compact(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def keyword_matches(text: str, keyword: str) -> bool:
        haystack = TextProcessor.normalize(text)
        needle = TextProcessor.normalize(keyword)
        if not needle:
            return False
        if " " in needle:
            return needle in haystack
        tokens = haystack.split()
        if len(needle) <= 3:
            return needle in tokens
        return any(token == needle or token.startswith(needle) for token in tokens)

    @classmethod
    def contains_any(cls, text: str, keywords: list[str]) -> bool:
        return any(cls.keyword_matches(text, kw) for kw in keywords)

    @classmethod
    def rough_phrase_match(cls, text: str, phrase: str) -> bool:
        haystack = cls.normalize(text)
        needle = cls.normalize(phrase)
        if not needle:
            return False
        if needle in haystack:
            return True
        tokens = haystack.split()
        words = needle.split()
        if not words:
            return False
        hits = 0
        for word in words:
            if len(word) <= 3:
                found = word in tokens
            else:
                stem = word[: min(7, len(word))]
                found = any(token.startswith(stem) for token in tokens)
            if found:
                hits += 1
        return hits == len(words)

    def is_training_or_exercise(self, text: str) -> bool:
        norm = self.normalize(text)
        exercise_terms = [
            "боевой подготовки",
            "боевая подготовка",
            "тактико специальн",
            "тактических заняти",
            "отработали совместные действия",
            "отработали навыки",
            "отработали практические",
            "провел учения",
            "провели учения",
            "проходят учения",
            "прошли учения",
            "тренировк",
            "тренировались",
            "учебные стрельбы",
            "учебных стрельб",
            "учебных целей",
            "учебных задач",
            "полигон",
            "полигоне",
            "центр боевой подготовки",
        ]
        return any(term in norm for term in exercise_terms)

    def is_ignored(self, text: str) -> bool:
        norm = self.normalize(text)
        ad_clickbait_terms = [
            "создать телеграм каналы",
            "создать телеграм канал",
            "телеграм каналы для оповещения",
            "каналы не будут блокировать",
            "ищите свой регион",
            "ищи свой регион",
            "ссылка в описании",
            "переходи по ссылке",
            "вход по ссылке",
            "подпишись на резерв",
            "резервный канал",
            "запасной канал",
            "закрытый канал",
            "доступ открыт",
            "успей подписаться",
            "читать далее",
            "продолжение в источнике",
            "источник в закрепе",
        ]
        if any(term in norm for term in ad_clickbait_terms):
            return True
        if self.is_training_or_exercise(text):
            return True
        return self.contains_any(text, self.ignore_keywords)

    def is_weather(self, text: str) -> bool:
        return self.contains_any(text, WEATHER_TERMS)

    def is_aviation_only(self, text: str) -> bool:
        if self.contains_any(text, DRONE_TERMS) or self.contains_any(text, ROCKET_TERMS):
            return False
        return self.contains_any(text, AVIATION_ONLY_TERMS)

    def has_alarm_context(self, text: str) -> bool:
        return (
            self.contains_any(text, DRONE_TERMS)
            or self.contains_any(text, ROCKET_TERMS)
            or self.contains_any(text, ALARM_TERMS)
        )

    def classify(self, text: str) -> DangerKind:
        if self.is_weather(text):
            return DangerKind.OTHER
        if self.is_aviation_only(text):
            return DangerKind.OTHER
        if self.contains_any(text, CLEAR_TERMS) and self.has_alarm_context(text):
            return DangerKind.CLEAR
        if self.contains_any(text, DRONE_TERMS):
            return DangerKind.DRONE
        if self.contains_any(text, ROCKET_TERMS):
            return DangerKind.ROCKET
        if self.contains_any(text, ALARM_TERMS):
            return DangerKind.ALARM
        return DangerKind.OTHER

    def extract_locations(self, text: str, source: SourceConfig) -> list[str]:
        result: list[str] = []
        for loc in source.locations:
            if self.normalize(loc) not in {"россия", "рф", "вся россия"}:
                result.append(loc)

        for region in self.regions:
            names = [region.name, *region.aliases]
            if any(self.rough_phrase_match(text, name) for name in names):
                result.append(region.name)
            for city in region.cities:
                cnames = [city.name, *city.aliases]
                if any(self.rough_phrase_match(text, cname) for cname in cnames):
                    result.append(city.name)

        seen: set[str] = set()
        unique: list[str] = []
        for item in result:
            k = self.normalize(item)
            if k and k not in seen:
                seen.add(k)
                unique.append(item)

        if not unique:
            for loc in source.locations:
                if self.normalize(loc) in {"россия", "рф", "вся россия"}:
                    unique.append("Россия")
                    break
        return unique or ["Россия"]

    @staticmethod
    def parse_date_bucket(value: str | None) -> str:
        if not value:
            return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
        except Exception:
            match = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", value)
            if match:
                day, month, year = match.groups()
                if len(year) == 2:
                    year = "20" + year
                return f"{year}-{int(month):02d}-{int(day):02d}"
            return datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")

    @classmethod
    def canonical_text(cls, text: str) -> str:
        val = cls.normalize(text)
        val = re.sub(r"https?\s+\S+", " ", val)
        val = re.sub(r"t me\s+\S+", " ", val)
        val = re.sub(r"\b\d{1,2}[:.]\d{2}\b", " время ", val)
        val = re.sub(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", " дата ", val)
        return cls.compact(val)[:1400]

    @staticmethod
    def hash_parts(*parts: str) -> str:
        raw = "\n".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def create_notice(
        self,
        source: SourceConfig,
        title: str,
        text: str,
        url: str,
        published_at: str | None,
    ) -> Notice:
        combined = self.compact(f"{title} {text}")
        kind = self.classify(combined)
        locations = self.extract_locations(combined, source)
        date_bucket = self.parse_date_bucket(published_at)
        loc_key = ",".join(self.normalize(x) for x in locations)
        notice_id = self.hash_parts(kind.value, date_bucket, loc_key, self.canonical_text(combined))

        return Notice(
            item_id=notice_id,
            source_name=source.name,
            source_url=source.url,
            title=self.compact(title)[:500],
            text=self.strip_noise(text)[:2200],
            url=url or source.url,
            published_at=published_at,
            locations=locations,
            kind=kind,
        )

    @classmethod
    def strip_noise(cls, text: str) -> str:
        val = re.sub(r"https?://\S+", "", text)
        val = re.sub(r"t\.me/\S+", "", val)
        val = re.sub(r"@[A-Za-z0-9_]+", "", val)
        cutoff_patterns = [
            r"[❗!*🔹]*\s*Радар по всей России\b.*$",
            r"[🌐]*\s*Обход белых списков\b.*$",
            r"[🔹*]*\s*Канал Минобороны России\b.*$",
            r"\bКанал Минобороны\b.*$",
            r"\bПодписывай(?:ся|тесь)\b.*$",
            r"\bМЧС России в M(?:A|А)X\b.*$",
            r"\bМЧС России в МАКС\b.*$",
            r"\bМы в M(?:A|А)X\b.*$",
            r"\bМы в МАКС\b.*$",
            r"\bБольше информации тут\b.*$",
            r"\bИнтернет[_ -]?Boost[_ -]?bot\b.*$",
            r"\bInternet[_ -]?Boost[_ -]?bot\b.*$",
            r"\bисточник мощных новостей\b.*$",
        ]
        for pat in cutoff_patterns:
            val = re.sub(pat, "", val, flags=re.IGNORECASE)
        val = re.sub(r"\s+[-—]\s*$", "", val)
        return cls.compact(val)

    def is_summary_or_stats(self, text: str) -> bool:
        norm = self.normalize(text)
        summary_markers = [
            "за прошедшую ночь",
            "в течение прошедшей ночи",
            "за минувшую ночь",
            "за сутки",
            "уничтожено",
            "перехвачено",
            "сбито",
            "сбиты",
            "уничтожены",
            "перехвачены",
            "дежурными средствами пво",
            "дежурными силами пво",
            "средствами пво",
        ]
        count_hits = sum(1 for marker in summary_markers if marker in norm)
        regions_found = [r.name for r in self.regions if self.normalize(r.name) in norm or any(self.normalize(a) in norm for a in r.aliases)]
        if len(regions_found) >= 3 and any(m in norm for m in ["ночь", "сутки", "дежурными"]):
            return True
        if count_hits >= 2 and re.search(r"\b\d{2,4}\s*(бпла|беспилотник|дрон)", norm):
            return True
        return False

    def is_relevant_for_region(self, notice: Notice, region: str, city: str = "") -> bool:
        if self.is_summary_or_stats(notice.text or notice.title):
            return False
        
        reg_norm = self.normalize(region)
        city_norm = self.normalize(city) if city else ""
        n_locs = {self.normalize(l) for l in notice.locations}

        if city_norm and city_norm in n_locs:
            return True
        if reg_norm in n_locs:
            return True

        full_text = self.normalize(f"{notice.title} {notice.text} {' '.join(notice.locations)}")
        if city_norm and self.rough_phrase_match(full_text, city):
            return True
        return self.rough_phrase_match(full_text, region)

    def trigger_sentences(self, text: str) -> list[str]:
        cleaned = self.strip_noise(text)
        parts = [p.strip(" -—•\n\t") for p in re.split(r"(?<=[.!?])\s+|\n+", cleaned) if p.strip()]
        danger_parts = [p for p in parts if self.classify(p) != DangerKind.OTHER]
        if danger_parts:
            return danger_parts[:3]
        return parts[:2]

    def incident_key(self, notice: Notice) -> str:
        visible = f"{notice.title}. {notice.text}" if notice.title and notice.text else (notice.title or notice.text)
        anchor = " ".join(self.trigger_sentences(visible)) or visible
        loc_key = ",".join(self.normalize(x) for x in notice.locations)
        date_bucket = self.parse_date_bucket(notice.published_at)
        return self.hash_parts(notice.kind.value, date_bucket, loc_key, self.canonical_text(anchor)[:900])

    def group_into_incidents(self, notices: list[Notice]) -> list[Incident]:
        buckets: dict[str, list[Notice]] = {}
        order: list[str] = []

        seen_ids: set[str] = set()
        seen_texts: set[str] = set()
        deduped: list[Notice] = []

        for n in notices:
            if n.item_id in seen_ids:
                continue
            text_key = self.hash_parts(
                n.kind.value,
                ",".join(self.normalize(x) for x in n.locations),
                self.canonical_text(f"{n.title} {n.text}")[:900],
            )
            if text_key in seen_texts:
                continue
            seen_ids.add(n.item_id)
            seen_texts.add(text_key)
            deduped.append(n)

        for n in deduped:
            key = self.incident_key(n)
            if key not in buckets:
                buckets[key] = []
                order.append(key)
            buckets[key].append(n)

        incidents: list[Incident] = []
        for key in order:
            items = buckets[key]
            first = items[0]
            locs: list[str] = []
            loc_seen: set[str] = set()
            for it in items:
                for l in it.locations:
                    norm = self.normalize(l)
                    if norm and norm not in loc_seen:
                        loc_seen.add(norm)
                        locs.append(l)
            incidents.append(
                Incident(
                    key=key,
                    kind=first.kind,
                    locations=locs,
                    notices=items,
                )
            )

        return sorted(
            incidents,
            key=lambda inc: max((n.published_at or "" for n in inc.notices), default=""),
            reverse=True,
        )
