import aiohttp
from app.config.settings import settings

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 bpla24-bot/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json;q=0.9,*/*;q=0.8",
}


async def http_get_text(session: aiohttp.ClientSession, url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=settings.http_timeout_seconds)
    async with session.get(url, headers=DEFAULT_HEADERS, timeout=timeout) as response:
        response.raise_for_status()
        return await response.text()


async def http_get_json(session: aiohttp.ClientSession, url: str) -> dict:
    timeout = aiohttp.ClientTimeout(total=settings.http_timeout_seconds)
    async with session.get(url, headers=DEFAULT_HEADERS, timeout=timeout) as response:
        response.raise_for_status()
        return await response.json(content_type=None)
