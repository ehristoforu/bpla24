import json
import pytest
from app.config.settings import Settings
from app.models.schemas import DangerKind, ScopeType, SourceConfig, SourceKind, Subscriber, Notice, Incident
from app.nlp.processor import TextProcessor
from app.services.formatter_service import FormatterService
from app.services.info_service import InfoService


def test_sources_json_validity():
    """Проверка корректности структуры и JSON-синтаксиса в sources.json"""
    with open("data/sources.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "keywords" in data
    assert "clear_keywords" in data
    assert "ignore_keywords" in data
    assert "regions" in data
    assert len(data["regions"]) > 0


def test_text_processor_classification():
    """Тестирование классификации типов угроз (БПЛА, ракеты, отбой)"""
    processor = TextProcessor("data/sources.json")

    # БПЛА
    assert processor.classify("Внимание! Угроза атаки БПЛА в регионе") == DangerKind.DRONE
    # Ракетная опасность
    assert processor.classify("Ракетная опасность! Всем в укрытие") == DangerKind.ROCKET
    # Отбой
    assert processor.classify("Отбой опасности атаки БПЛА") == DangerKind.CLEAR
    # Погода (игнорируется / OTHER)
    assert processor.classify("Штормовое предупреждение: сильный ветер и дождь") == DangerKind.OTHER


def test_text_processor_noise_stripping():
    """Тестирование очистки ссылок, упоминаний и рекламных вставок"""
    raw = "Внимание! https://t.me/example @channel Радар по всей России"
    cleaned = TextProcessor.strip_noise(raw)
    assert "https://" not in cleaned
    assert "@channel" not in cleaned
    assert "Радар по всей России" not in cleaned


def test_text_processor_location_extraction():
    """Тестирование извлечения локаций"""
    processor = TextProcessor("data/sources.json")
    src = SourceConfig(name="Тест", kind=SourceKind.TELEGRAM, url="https://t.me/test", locations=["Москва"])
    notice = processor.create_notice(
        source=src,
        title="Опасность",
        text="В Белгородской области объявлена ракетная опасность",
        url="",
        published_at="2026-08-28T12:00:00Z",
    )
    assert notice.kind == DangerKind.ROCKET
    assert any("Белгородская область" in loc for loc in notice.locations)


def test_formatter_service():
    """Тестирование форматирования инцидентов и статуса"""
    notice = Notice(
        item_id="123",
        source_name="МЧС",
        source_url="https://t.me/mchs",
        title="Угроза БПЛА",
        text="Внимание всем",
        url="https://t.me/mchs/1",
        published_at="2026-08-28T12:00:00Z",
        locations=["Курская область"],
        kind=DangerKind.DRONE,
    )
    incident = Incident(
        key="inc_123",
        kind=DangerKind.DRONE,
        locations=["Курская область"],
        notices=[notice],
    )
    status_text = FormatterService.build_status(
        scope=ScopeType.REGION,
        region="Курская область",
        city="Курск",
        incidents=[incident],
        updated_at=None,
    )
    assert "Курская область" in status_text
    assert "УГРОЗА БПЛА" in status_text


def test_info_service_guides():
    """Тестирование генерации памяток и правовой информации"""
    safety = InfoService.get_safety_guide()
    legal = InfoService.get_legal_disclaimer()
    about = InfoService.get_about()

    assert "112" in safety
    assert "ПВО" in legal
    assert "БПЛА24" in about
