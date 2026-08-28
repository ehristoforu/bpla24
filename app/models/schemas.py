from enum import Enum
from pydantic import BaseModel, Field


class DangerKind(str, Enum):
    DRONE = "drone"
    ROCKET = "rocket"
    ALARM = "alarm"
    CLEAR = "clear"
    OTHER = "other"


class ScopeType(str, Enum):
    ALL = "all"
    REGION = "region"


class SourceKind(str, Enum):
    TELEGRAM = "telegram"
    RSS = "rss"
    HTML = "html"
    RADAR_API = "radar_api"


class SourceConfig(BaseModel):
    name: str
    kind: SourceKind
    url: str
    locations: list[str] = Field(default_factory=list)
    channel: str = ""


class CityConfig(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)


class RegionConfig(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    cities: list[CityConfig] = Field(default_factory=list)
    sources: list[SourceConfig] = Field(default_factory=list)


class Notice(BaseModel):
    item_id: str
    source_name: str
    source_url: str
    title: str
    text: str
    url: str
    published_at: str | None = None
    locations: list[str] = Field(default_factory=list)
    kind: DangerKind = DangerKind.OTHER


class Incident(BaseModel):
    key: str
    kind: DangerKind
    locations: list[str]
    notices: list[Notice]


class Subscriber(BaseModel):
    user_id: int
    region: str
    city: str
    notify_scope: ScopeType = ScopeType.REGION
    is_active: bool = True
    updated_at: str
