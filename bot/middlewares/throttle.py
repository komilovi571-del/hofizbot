"""
Throttle Middleware — per-user rate limiting.

Redis asosida ishlaydi:
- Har bir foydalanuvchi uchun daqiqadagi so'rovlar soni hisoblanadi
- Limit oshsa, xabar yuboriladi va so'rov rad etiladi
"""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from bot.services.cache import CacheService

logger = logging.getLogger(__name__)


class ThrottleMiddleware(BaseMiddleware):
    """
    Rate limiting middleware.

    Har bir foydalanuvchiga daqiqada cheklangan miqdorda so'rov yuborish imkonini beradi.
    Admin foydalanuvchilar uchun limit qo'llanmaydi.
    """

    def __init__(self, rate_limit: int = 5, window: int = 60, admin_ids: list[int] | None = None):
        """
        Args:
            rate_limit: Daqiqadagi maksimal so'rovlar soni.
            window: Vaqt oynasi (soniyalarda).
            admin_ids: Admin foydalanuvchilar ro'yxati (limit qo'llanmaydi).
        """
        self.rate_limit = rate_limit
        self.window = window
        self.admin_ids = admin_ids or []

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Middleware ishlash logikasi."""
        # Faqat message turidagi event-lar uchun
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if not user_id:
            return await handler(event, data)

        # Foydalanuvchini kuzatish (bir marta, handler'dan oldin)
        stats_service = data.get("stats_service")
        if stats_service:
            stats_service.track_user(
                user_id,
                username=event.from_user.username or "",
                full_name=event.from_user.full_name or "",
            )
            # Ban tekshirish
            if stats_service.is_banned(user_id):
                try:
                    await event.reply("🚫 Siz ban qilingansiz.")
                except Exception:
                    pass
                return None

        # Buyruqlar uchun rate limit qo'llanmaydi
        if event.text and event.text.startswith("/"):
            return await handler(event, data)

        # Admin uchun limit qo'llanmaydi
        if user_id in self.admin_ids:
            return await handler(event, data)

        # Cache service ni olish
        cache_service: CacheService | None = data.get("cache_service")
        if not cache_service:
            return await handler(event, data)

        # Rate limit tekshirish
        allowed = await cache_service.check_rate_limit(
            user_id=user_id,
            limit=self.rate_limit,
            window=self.window,
        )

        if not allowed:
            logger.info(f"Rate limit: user={user_id}")
            await event.reply(
                "⏳ <b>Juda ko'p so'rov!</b>\n\n"
                f"Daqiqada {self.rate_limit} ta so'rov yuborishingiz mumkin.\n"
                "Biroz kuting va qaytadan urinib ko'ring.",
                parse_mode="HTML",
            )
            return None

        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """Barcha xabarlarni loglash (track_user ThrottleMiddleware'da bajariladi)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.from_user:
            logger.info(
                f"Message: user={event.from_user.id} "
                f"({event.from_user.full_name}) | "
                f"text={event.text[:50] if event.text else 'N/A'}"
            )
        return await handler(event, data)
