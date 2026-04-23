"""i18n Middleware — foydalanuvchining tilini handler'ga inject qiladi."""

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message, TelegramObject

from bot.i18n import DEFAULT_LANG, normalize_lang

logger = logging.getLogger(__name__)


class I18nMiddleware(BaseMiddleware):
    """Har bir handler uchun ``data["lang"]`` ni to'ldiradi.

    Tanlash tartibi:
    1. StatsService'dan saqlangan til (agar foydalanuvchi /lang orqali tanlagan bo'lsa)
    2. Telegram ``language_code`` (birinchi marta)
    3. DEFAULT_LANG (uz)
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, (Message, CallbackQuery, InlineQuery)):
            user = event.from_user

        lang = DEFAULT_LANG
        if user:
            stats_service = data.get("stats_service")
            saved = stats_service.get_lang(user.id) if stats_service else None
            if saved:
                lang = saved
            else:
                lang = normalize_lang(user.language_code)

        data["lang"] = lang
        return await handler(event, data)
