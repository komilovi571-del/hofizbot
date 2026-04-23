"""
Inline Mode Handler — inline rejimda musiqa qidirish.

Foydalanuvchi @botusername qo'shiq_nomi yozganda
YouTube'dan natijalarni ko'rsatish.
"""

import hashlib
import json
import logging

from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)

from bot.services.cache import CacheService
from bot.services.shazam import search_songs

logger = logging.getLogger(__name__)

router = Router(name="inline")

# Inline qidiruv natijalari Redis'da keshlanadi (10 daqiqa)
_INLINE_CACHE_TTL = 600


async def _cached_search(
    cache_service: CacheService | None, query: str, limit: int
) -> list[dict]:
    """YouTube search natijalarini Redis orqali keshlash."""
    cache_key = f"inline_search:{hashlib.md5(query.lower().encode()).hexdigest()}:{limit}"
    if cache_service and cache_service._redis:
        try:
            raw = await cache_service._redis.get(cache_key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass

    songs = await search_songs(query, limit=limit)

    if cache_service and cache_service._redis and songs:
        try:
            await cache_service._redis.setex(
                cache_key, _INLINE_CACHE_TTL, json.dumps(songs)
            )
        except Exception:
            pass

    return songs


@router.inline_query()
async def handle_inline_query(
    query: InlineQuery,
    cache_service: CacheService = None,
) -> None:
    """Inline rejimda musiqa qidirish."""
    text = query.query.strip()

    if not text or len(text) < 2:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="🎵 Musiqa qidirish",
                description="Qo'shiq nomi yoki san'atkor ismini yozing...",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "🎵 Menga qo'shiq nomi yoki san'atkor ismini yozing "
                        "va men uni yuklab beraman!"
                    ),
                ),
                thumbnail_url="https://img.icons8.com/color/96/music.png",
            )
        ]
        await query.answer(results, cache_time=5, is_personal=True)
        return

    try:
        songs = await _cached_search(cache_service, text, limit=15)

        if not songs:
            results = [
                InlineQueryResultArticle(
                    id="not_found",
                    title="❌ Natija topilmadi",
                    description=f"'{text}' bo'yicha hech narsa topilmadi",
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ '{text}' bo'yicha natija topilmadi.",
                    ),
                )
            ]
            await query.answer(results, cache_time=30, is_personal=True)
            return

        results = []
        for i, song in enumerate(songs):
            title = song.get("title", "Noma'lum")
            channel = song.get("channel", "")
            duration = song.get("duration", 0)
            url = song.get("url", "")
            thumb = song.get("thumbnail", "")

            # Duration formatlash
            if duration:
                mins, secs = divmod(int(duration), 60)
                dur_str = f"{mins}:{secs:02d}"
            else:
                dur_str = ""

            desc_parts = []
            if channel:
                desc_parts.append(f"🎤 {channel}")
            if dur_str:
                desc_parts.append(f"⏱ {dur_str}")
            description = " | ".join(desc_parts) if desc_parts else "YouTube"

            result_id = hashlib.md5(f"{url}{i}".encode()).hexdigest()[:16]

            # URL ni chat ga yuborish — bot text handlerde ushlab oladi
            article = InlineQueryResultArticle(
                id=result_id,
                title=f"🎵 {title}",
                description=description,
                input_message_content=InputTextMessageContent(
                    message_text=url if url else f"🎵 {title}",
                ),
                thumbnail_url=thumb if thumb else None,
            )
            results.append(article)

        button = InlineQueryResultsButton(
            text="🎵 Botga o'tish",
            start_parameter="inline",
        )

        await query.answer(
            results,
            cache_time=300,
            is_personal=False,
            button=button,
        )

    except Exception as e:
        logger.error(f"Inline query xatosi: {e}", exc_info=True)
        results = [
            InlineQueryResultArticle(
                id="error",
                title="❌ Xato yuz berdi",
                description="Qaytadan urinib ko'ring",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Qidirishda xato. Qaytadan urinib ko'ring.",
                ),
            )
        ]
        await query.answer(results, cache_time=5, is_personal=True)
