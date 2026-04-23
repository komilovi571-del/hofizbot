"""Channels Service — admin kanallarini Redis'da saqlash.

Redis struktura:
    HASH  "admin:channels:<admin_id>"
        field = chat_id (str), value = json({title, username, added_at})

Agar Redis mavjud bo'lmasa — in-memory fallback (xotirada saqlanadi, bot restart'da yo'qoladi).
"""

import json
import logging
import time
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ChannelsService:
    """Admin kanallarini boshqarish."""

    def __init__(self, redis_client: redis.Redis | None = None):
        self._redis = redis_client
        # Fallback: xotirada saqlash (admin_id → {chat_id → meta})
        self._mem: dict[int, dict[int, dict[str, Any]]] = {}

    def set_redis(self, client: redis.Redis | None) -> None:
        """Redis ulangandan keyin client'ni o'rnatish."""
        self._redis = client

    @staticmethod
    def _key(admin_id: int) -> str:
        return f"admin:channels:{admin_id}"

    async def add_channel(
        self,
        admin_id: int,
        chat_id: int,
        title: str = "",
        username: str = "",
    ) -> None:
        """Kanalni qo'shish (agar mavjud bo'lsa — yangilanadi)."""
        meta = {
            "title": title,
            "username": username,
            "added_at": int(time.time()),
        }
        if self._redis:
            try:
                await self._redis.hset(
                    self._key(admin_id), str(chat_id), json.dumps(meta)
                )
                return
            except Exception as e:
                logger.warning(f"ChannelsService.add Redis xato: {e}")
        self._mem.setdefault(admin_id, {})[chat_id] = meta

    async def remove_channel(self, admin_id: int, chat_id: int) -> bool:
        """Kanalni olib tashlash."""
        if self._redis:
            try:
                n = await self._redis.hdel(self._key(admin_id), str(chat_id))
                return bool(n)
            except Exception as e:
                logger.warning(f"ChannelsService.remove Redis xato: {e}")
        d = self._mem.get(admin_id, {})
        if chat_id in d:
            d.pop(chat_id, None)
            return True
        return False

    async def list_channels(self, admin_id: int) -> list[dict[str, Any]]:
        """Admin'ning barcha kanallari (chat_id, title, username, added_at)."""
        result: list[dict[str, Any]] = []
        if self._redis:
            try:
                data = await self._redis.hgetall(self._key(admin_id))
                for cid, raw in (data or {}).items():
                    try:
                        meta = json.loads(raw)
                    except Exception:
                        meta = {}
                    result.append({"chat_id": int(cid), **meta})
                return result
            except Exception as e:
                logger.warning(f"ChannelsService.list Redis xato: {e}")
        # Fallback
        for cid, meta in (self._mem.get(admin_id) or {}).items():
            result.append({"chat_id": cid, **meta})
        return result

    async def get_channel(self, admin_id: int, chat_id: int) -> dict[str, Any] | None:
        """Bitta kanal ma'lumoti."""
        if self._redis:
            try:
                raw = await self._redis.hget(self._key(admin_id), str(chat_id))
                if raw:
                    meta = json.loads(raw)
                    return {"chat_id": chat_id, **meta}
                return None
            except Exception as e:
                logger.warning(f"ChannelsService.get Redis xato: {e}")
        meta = (self._mem.get(admin_id) or {}).get(chat_id)
        if meta:
            return {"chat_id": chat_id, **meta}
        return None
