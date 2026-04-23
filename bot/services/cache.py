"""
Redis Cache Service — Telegram file_id saqlash va olish.

Bu eng muhim tezlik optimizatsiyasi:
- Bir marta yuklangan fayl qayta so'ralganda, hech narsa yuklamaydi
- Telegram file_id orqali darhol yuboriladi (0 soniya)
- Virusli kontentda juda samarali (bir xil URL minglab marta so'raladi)
"""

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class CacheService:
    """
    Redis-based cache service.

    Telegram file_id larni saqlash va olish orqali
    takroriy so'rovlarga darhol javob berish.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl: int = 48 * 3600):
        self.redis_url = redis_url
        self.ttl = ttl  # 48 soat default
        self._redis: redis.Redis | None = None

    async def connect(self) -> None:
        """Redis ulanishini o'rnatish."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            await self._redis.ping()
            logger.info("✅ Redis ulandi")
        except Exception as e:
            logger.warning(f"⚠️ Redis ulanish xatosi: {e}. Cache ishlamaydi.")
            self._redis = None

    async def disconnect(self) -> None:
        """Redis ulanishini yopish."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis ulanish yopildi")

    @property
    def redis(self) -> redis.Redis | None:
        """Xom Redis client (boshqa servislar foydalanishi uchun)."""
        return self._redis

    @staticmethod
    def _make_key(url: str, media_type: str, quality: str = "") -> str:
        """Cache kalitini yaratish."""
        raw = f"{url}:{media_type}:{quality}"
        return f"media:{hashlib.sha256(raw.encode()).hexdigest()}"

    async def get_file_id(self, url: str, media_type: str, quality: str = "") -> dict[str, Any] | None:
        """
        Cache'dan file_id olish.

        Returns:
            dict with 'file_id', 'title', 'duration', 'file_type' or None
        """
        if not self._redis:
            return None

        try:
            key = self._make_key(url, media_type, quality)
            data = await self._redis.get(key)
            if data:
                logger.info(f"✅ Cache HIT: {key[:20]}...")
                return json.loads(data)
            logger.debug(f"Cache MISS: {key[:20]}...")
            return None
        except Exception as e:
            logger.warning(f"Cache o'qish xatosi: {e}")
            return None

    async def set_file_id(
        self,
        url: str,
        media_type: str,
        quality: str,
        file_id: str,
        title: str = "",
        duration: int = 0,
        file_type: str = "video",
    ) -> None:
        """
        file_id ni cache'ga saqlash.

        Keyingi safar shu URL so'ralganda darhol yuboriladi.
        """
        if not self._redis:
            return

        try:
            key = self._make_key(url, media_type, quality)
            data = json.dumps({
                "file_id": file_id,
                "title": title,
                "duration": duration,
                "file_type": file_type,
            })
            await self._redis.setex(key, self.ttl, data)
            logger.info(f"✅ Cache SAVED: {key[:20]}... | {title[:30]}")
        except Exception as e:
            logger.warning(f"Cache yozish xatosi: {e}")

    async def get_user_downloads(self, user_id: int) -> int:
        """Foydalanuvchining faol yuklashlari sonini olish."""
        if not self._redis:
            return 0

        try:
            key = f"user_downloads:{user_id}"
            count = await self._redis.get(key)
            return int(count) if count else 0
        except Exception:
            return 0

    async def increment_user_downloads(self, user_id: int, ttl: int = 300) -> int:
        """Foydalanuvchi yuklashlari sonini oshirish."""
        if not self._redis:
            return 0

        try:
            key = f"user_downloads:{user_id}"
            count = await self._redis.incr(key)
            await self._redis.expire(key, ttl)
            return count
        except Exception:
            return 0

    async def decrement_user_downloads(self, user_id: int) -> None:
        """Foydalanuvchi yuklashlari sonini kamaytirish."""
        if not self._redis:
            return

        try:
            key = f"user_downloads:{user_id}"
            count = await self._redis.decr(key)
            if count <= 0:
                await self._redis.delete(key)
        except Exception:
            pass

    async def check_rate_limit(self, user_id: int, limit: int = 5, window: int = 60) -> bool:
        """
        Rate limit tekshirish.

        Returns:
            True — agar limit oshilmagan bo'lsa (ruxsat beriladi)
            False — agar limit oshilgan bo'lsa (rad etiladi)
        """
        if not self._redis:
            return True  # Redis yo'q bo'lsa, limitsiz

        try:
            key = f"rate:{user_id}"
            current = await self._redis.get(key)

            if current and int(current) >= limit:
                return False

            pipe = self._redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, window)
            await pipe.execute()
            return True
        except Exception:
            return True  # Redis xatosida limitsiz

    async def get_stats(self) -> dict[str, Any]:
        """Bot statistikasini olish."""
        if not self._redis:
            return {"status": "disconnected"}

        try:
            info = await self._redis.info("memory")
            db_size = await self._redis.dbsize()
            return {
                "status": "connected",
                "cached_items": db_size,
                "memory_used": info.get("used_memory_human", "N/A"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
