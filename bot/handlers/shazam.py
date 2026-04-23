"""
Shazam Handler — musiqani aniqlash va yuklab berish.

Foydalanuvchi audio/voice/video_note xabar yuborganda
Shazam orqali qo'shiq nomini aniqlash va YouTube'dan yuklab berish.
"""

import asyncio
import hashlib
import logging
import os
import time

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.downloader import Downloader
from bot.services.shazam import recognize_from_telegram_file, search_and_download_song
from bot.services.stats import StatsService
from bot.utils.lru import TTLCache

logger = logging.getLogger(__name__)

router = Router(name="shazam")

# Shazam natijalarini saqlash (callback uchun) — TTL + LRU
_shazam_results: TTLCache[str, dict] = TTLCache(maxsize=10_000, ttl=6 * 3600)


def _build_shazam_keyboard(result_id: str):
    """Shazam natijasi uchun inline keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🎵 Musiqani yuklab olish", callback_data=f"shazam_dl:{result_id}")
    return builder.as_markup()


@router.message(F.audio | F.voice | F.video_note)
async def handle_audio_for_shazam(
    message: Message,
    bot: Bot,
    downloader: Downloader = None,
    stats_service: StatsService = None,
) -> None:
    """Audio/voice/video_note yuborilganda Shazam orqali aniqlash."""
    # file_id ni aniqlash
    if message.audio:
        file_id = message.audio.file_id
    elif message.voice:
        file_id = message.voice.file_id
    elif message.video_note:
        file_id = message.video_note.file_id
    else:
        return

    if stats_service:
        stats_service.increment_shazam()

    temp_dir = downloader.temp_dir if downloader else "./tmp"

    # Status xabar
    status_msg = await message.reply(
        "🎵 <b>Musiqa aniqlanmoqda...</b>\n\n"
        "🔍 Shazam orqali qidirilmoqda...",
        parse_mode="HTML",
    )

    temp_path: str | None = None
    try:
        result, temp_path = await recognize_from_telegram_file(
            bot=bot,
            file_id=file_id,
            temp_dir=temp_dir,
        )

        if result.found:
            # Natijani saqlash (keyinchalik yuklab olish uchun)
            result_id = hashlib.md5(
                f"{result.title}:{result.artist}".encode()
            ).hexdigest()[:12]
            _shazam_results[result_id] = {
                "title": result.title,
                "artist": result.artist,
                "album": result.album,
                "cover_url": result.cover_url,
            }

            # Natija xabari
            text_parts = [
                f"🎵 <b>{result.title}</b>",
                f"🎤 {result.artist}",
            ]

            if result.album:
                text_parts.append(f"💿 {result.album}")
            if result.year:
                text_parts.append(f"📅 {result.year}")
            if result.genre:
                text_parts.append(f"🏷 {result.genre}")

            text_parts.append("")  # Bo'sh qator

            # Linklar
            links = []
            if result.apple_music_url:
                links.append(f'🍎 <a href="{result.apple_music_url}">Apple Music</a>')
            if result.shazam_url:
                links.append(f'🟢 <a href="{result.shazam_url}">Shazam</a>')

            if links:
                text_parts.append(" | ".join(links))

            text = "\n".join(text_parts)
            keyboard = _build_shazam_keyboard(result_id)

            if result.cover_url:
                try:
                    await status_msg.delete()
                    await message.reply_photo(
                        photo=result.cover_url,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                except Exception:
                    await status_msg.edit_text(
                        text, parse_mode="HTML", reply_markup=keyboard
                    )
            else:
                await status_msg.edit_text(
                    text, parse_mode="HTML", reply_markup=keyboard
                )
        else:
            await status_msg.edit_text(
                f"❌ <b>Qo'shiq aniqlanmadi</b>\n\n"
                f"{result.error_message or 'Boshqa qismini yuboring yoki aniqroq audio yuboring.'}",
                parse_mode="HTML",
            )

    except Exception as e:
        logger.error(f"Shazam handler xatosi: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Xato yuz berdi:</b> {str(e)[:200]}",
            parse_mode="HTML",
        )
    finally:
        # Temp faylni o'chirish
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.callback_query(F.data.startswith("shazam_dl:"))
async def handle_shazam_download(
    callback: CallbackQuery,
    bot: Bot,
    downloader: Downloader = None,
    stats_service: StatsService = None,
) -> None:
    """Shazam orqali aniqlangan qo'shiqni YouTube'dan yuklab berish."""
    result_id = callback.data.split(":")[1]

    song_data = _shazam_results.get(result_id)
    if not song_data:
        await callback.answer(
            "❌ Ma'lumot eskirgan. Qaytadan audio yuboring.", show_alert=True
        )
        return

    title = song_data["title"]
    artist = song_data["artist"]

    await callback.answer("⚡ Musiqa yuklab olinmoqda...")

    # Status xabar
    status_msg = await callback.message.reply(
        f"🎵 <b>Yuklab olinmoqda...</b>\n\n"
        f"🔍 <b>{artist} — {title}</b>\n"
        f"📥 YouTube'dan qidirilmoqda...",
        parse_mode="HTML",
    )

    downloaded_path = None
    try:
        start_time = time.time()

        # YouTube'dan qidirish va yuklab olish
        downloaded_path, song_title = await search_and_download_song(
            query=f"{artist} - {title}",
            temp_dir=downloader.temp_dir if downloader else "./tmp",
        )

        if not downloaded_path or not os.path.exists(downloaded_path):
            await status_msg.edit_text(
                f"❌ <b>Qo'shiq topilmadi</b>\n\n"
                f"YouTube'dan \"{artist} — {title}\" topilmadi.",
                parse_mode="HTML",
            )
            return

        download_time = time.time() - start_time
        filesize = os.path.getsize(downloaded_path)
        size_str = (
            f"{filesize / (1024*1024):.1f} MB"
            if filesize > 1024 * 1024
            else f"{filesize / 1024:.1f} KB"
        )

        await status_msg.edit_text(
            f"📤 <b>Telegramga yuborilmoqda...</b>\n\n"
            f"🎵 {artist} — {title}\n"
            f"📁 {size_str}",
            parse_mode="HTML",
        )

        # Telegramga yuborish
        input_file = FSInputFile(downloaded_path)
        caption = (
            f"🎵 <b>{title}</b>\n"
            f"🎤 {artist}\n"
            f"⚡ {download_time:.1f}s da yuklandi"
        )

        if song_data.get("album"):
            caption += f"\n💿 {song_data['album']}"

        await bot.send_audio(
            chat_id=callback.message.chat.id,
            audio=input_file,
            caption=caption,
            parse_mode="HTML",
            title=f"{artist} - {title}",
            performer=artist,
        )

        # Stats
        if stats_service and callback.from_user:
            stats_service.increment_downloads(callback.from_user.id)

        # Status xabarni o'chirish
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Shazam download xatosi: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Yuklab olishda xato:</b> {str(e)[:200]}",
            parse_mode="HTML",
        )
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
            except Exception:
                pass
