import os
from datetime import datetime, timezone
from pathlib import Path
import aiosqlite

from app.database.base import IDatabase
from app.models.schemas import Incident, ScopeType, Subscriber


class SqliteDatabase(IDatabase):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._connection: aiosqlite.Connection | None = None

    async def init(self) -> None:
        db_dir = Path(self.db_path).parent
        if not db_dir.exists():
            os.makedirs(db_dir, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                region TEXT NOT NULL,
                city TEXT NOT NULL,
                notify_scope TEXT NOT NULL DEFAULT 'region',
                is_active INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )
            """
        )

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sent_items (
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                PRIMARY KEY (user_id, item_id)
            )
            """
        )

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_stats (
                stat_name TEXT PRIMARY KEY,
                count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await self._connection.commit()

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def upsert_user(self, user_id: int, region: str, city: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        assert self._connection is not None
        await self._connection.execute(
            """
            INSERT INTO subscribers (user_id, region, city, notify_scope, is_active, updated_at)
            VALUES (?, ?, ?, 'region', 1, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                region = excluded.region,
                city = excluded.city,
                is_active = 1,
                updated_at = excluded.updated_at
            """,
            (user_id, region, city, now),
        )
        await self._connection.commit()

    async def get_user(self, user_id: int) -> Subscriber | None:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT user_id, region, city, notify_scope, is_active, updated_at FROM subscribers WHERE user_id = ? AND is_active = 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return Subscriber(
            user_id=row["user_id"],
            region=row["region"],
            city=row["city"],
            notify_scope=ScopeType(row["notify_scope"]),
            is_active=bool(row["is_active"]),
            updated_at=row["updated_at"],
        )

    async def list_users(self) -> list[Subscriber]:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT user_id, region, city, notify_scope, is_active, updated_at FROM subscribers WHERE is_active = 1"
        )
        rows = await cursor.fetchall()
        return [
            Subscriber(
                user_id=row["user_id"],
                region=row["region"],
                city=row["city"],
                notify_scope=ScopeType(row["notify_scope"]),
                is_active=bool(row["is_active"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    async def set_notify_scope(self, user_id: int, notify_scope: ScopeType) -> None:
        assert self._connection is not None
        now = datetime.now(timezone.utc).isoformat()
        await self._connection.execute(
            "UPDATE subscribers SET notify_scope = ?, updated_at = ? WHERE user_id = ?",
            (notify_scope.value, now, user_id),
        )
        await self._connection.commit()

    async def deactivate_user(self, user_id: int) -> None:
        assert self._connection is not None
        now = datetime.now(timezone.utc).isoformat()
        await self._connection.execute(
            "UPDATE subscribers SET is_active = 0, updated_at = ? WHERE user_id = ?",
            (now, user_id),
        )
        await self._connection.commit()

    async def was_sent(self, user_id: int, item_id: str) -> bool:
        assert self._connection is not None
        cursor = await self._connection.execute(
            "SELECT 1 FROM sent_items WHERE user_id = ? AND item_id = ?",
            (user_id, item_id),
        )
        row = await cursor.fetchone()
        return row is not None

    async def mark_incidents_sent(self, user_id: int, incidents: list[Incident]) -> None:
        assert self._connection is not None
        ids: list[str] = []
        for incident in incidents:
            ids.append(f"event:{incident.key}")
            ids.extend(notice.item_id for notice in incident.notices)
        if not ids:
            return
        now = datetime.now(timezone.utc).isoformat()
        await self._connection.executemany(
            "INSERT OR IGNORE INTO sent_items (user_id, item_id, sent_at) VALUES (?, ?, ?)",
            [(user_id, item_id, now) for item_id in ids],
        )
        await self._connection.commit()

    async def increment_stat(self, stat_name: str) -> None:
        assert self._connection is not None
        await self._connection.execute(
            """
            INSERT INTO bot_stats (stat_name, count) VALUES (?, 1)
            ON CONFLICT(stat_name) DO UPDATE SET count = count + 1
            """,
            (stat_name,),
        )
        await self._connection.commit()

    async def get_stats(self) -> dict[str, int]:
        assert self._connection is not None
        cursor = await self._connection.execute("SELECT stat_name, count FROM bot_stats")
        rows = await cursor.fetchall()
        return {row["stat_name"]: row["count"] for row in rows}

    async def count_subscribers(self) -> tuple[int, int]:
        assert self._connection is not None
        cursor_total = await self._connection.execute("SELECT COUNT(*) as cnt FROM subscribers")
        row_total = await cursor_total.fetchone()
        total = row_total["cnt"] if row_total else 0

        cursor_active = await self._connection.execute("SELECT COUNT(*) as cnt FROM subscribers WHERE is_active = 1")
        row_active = await cursor_active.fetchone()
        active = row_active["cnt"] if row_active else 0
        return total, active
