"""
Download Handler — Video va audio yuklab olish uchun asosiy handler.

Ish oqimi:
1. Foydalanuvchi URL yuboradi
2. URL tekshiriladi (platforma aniqlanadi)
3. Redis cache tekshiriladi (HIT → darhol yuboriladi)
4. Inline keyboard ko'rsatiladi (Video/Audio tanlash)
5. Foydalanuvchi tanlaydi → yt-dlp + aria2c bilan yuklab olinadi
6. Telegramga yuboriladi
7. file_id Redis cache-ga saqlanadi
"""

import asyncio
import hashlib
import logging
import os
import time

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    FSInputFile,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import Config
from bot.keyboards.inline import (
    get_cancel_keyboard,
    get_format_keyboard,
    get_quality_keyboard,
)
from bot.services.cache import CacheService
from bot.services.downloader import (
    AudioFormat,
    DownloadResult,
    Downloader,
    MediaType,
    VideoQuality,
)
from bot.services.audio_extractor import compress_video, ensure_h264
from bot.services.shazam import recognize_from_telegram_file, search_and_download_song, search_songs
from bot.services.stats import StatsService
from bot.services.url_parser import (
    Platform,
    get_platform_display,
    parse_url,
)
from bot.utils.lru import TTLCache

# Telegram Bot API fayl hajmi limiti.
# Local Bot API ishlatilsa 2GB, aks holda 49MB (1MB margin).
# Real qiymat Config orqali runtime'da aniqlanadi (_file_limit()).
TELEGRAM_FILE_LIMIT_DEFAULT = 49 * 1024 * 1024
TELEGRAM_FILE_LIMIT_LOCAL = 2_000 * 1024 * 1024  # ~2GB

logger = logging.getLogger(__name__)

router = Router(name="download")

# URL hash → URL mapping (xotirada, TTL bilan, RAM leak yo'q)
_url_store: TTLCache[str, str] = TTLCache(maxsize=20_000, ttl=6 * 3600)

# Qidiruv natijalari (hash → YouTube URL)
_search_results: TTLCache[str, str] = TTLCache(maxsize=20_000, ttl=3600)

# Qidiruv sahifalash: search_id → {"query": str, "songs": list, "page": int}
_search_pages: TTLCache[str, dict] = TTLCache(maxsize=5_000, ttl=3600)

PAGE_SIZE = 10  # Har sahifada 10 ta natija


def _file_limit(config: Config | None) -> int:
    """Konfiguratsiyaga qarab Telegram fayl limiti."""
    if config and config.telegram_api.local_bot_api_url:
        return TELEGRAM_FILE_LIMIT_LOCAL
    return TELEGRAM_FILE_LIMIT_DEFAULT


def _hash_url(url: str) -> str:
    """URL dan qisqa hash yaratish (callback_data uchun max 64 bayt)."""
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    return h


def _store_url(url: str) -> str:
    """URL ni saqlash va hash qaytarish."""
    h = _hash_url(url)
    _url_store[h] = url
    return h


def _get_url(url_hash: str) -> str | None:
    """Hash bo'yicha URL olish."""
    return _url_store.get(url_hash)


def _format_duration(seconds) -> str:
    """Soniyani mm:ss formatga o'tkazish."""
    if not seconds:
        return ""
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _format_size(size_bytes: int) -> str:
    """Baytni MB/GB ga o'tkazish."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


# =========================================================
#  Foydalanuvchi URL yuboradi
# =========================================================

@router.message(F.text & ~F.text.startswith("/"))
async def handle_url(
    message: Message,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    stats_service: StatsService = None,
    config: Config = None,
) -> None:
    """Foydalanuvchi yuborgan URL yoki qo'shiq nomini qabul qilish."""

    # Ban tekshirish (track_user/is_banned LoggingMiddleware'da bajariladi,
    # bu yerda takroran chaqirilmaydi)

    # URL ni aniqlash
    parsed = parse_url(message.text)

    if not parsed.is_valid:
        # URL topilmadi → musiqa qidirish
        text = message.text.strip()
        if len(text) >= 2:
            await _handle_music_search(
                message, bot, downloader, cache_service, stats_service, text
            )
            return
        await message.reply(parsed.error_message, parse_mode="HTML")
        return

    # Rate limit ThrottleMiddleware tomonidan bajariladi — bu yerda takroran yo'q

    # Foydalanuvchi yuklanishlari sonini tekshirish
    max_per_user = config.download.max_per_user if config else 3
    active = await cache_service.get_user_downloads(message.from_user.id)
    if active >= max_per_user:
        await message.reply(
            f"⏳ <b>Bir vaqtda {max_per_user} ta yuklab olish mumkin.</b>\n\n"
            "Oldingi yuklanishlar tugashini kuting.",
            parse_mode="HTML",
        )
        return

    # URL ni saqlash
    url_hash = _store_url(parsed.url)
    platform_name = get_platform_display(parsed.platform)

    # Format tanlash keyboard
    await message.reply(
        f"{platform_name} havolasi aniqlandi!\n\n"
        f"📥 <b>Nima yuklab olmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=get_format_keyboard(url_hash),
    )


# =========================================================
#  Musiqa qidirish (matn bo'yicha)
# =========================================================

def _build_search_page(search_id: str, page: int = 0) -> tuple[str, InlineKeyboardBuilder]:
    """Qidiruv natijasining berilgan sahifasi uchun matn va keyboard yaratish."""
    data = _search_pages.get(search_id)
    if not data:
        return "❌ Natija eskirgan.", InlineKeyboardBuilder()

    songs = data["songs"]
    query = data["query"]
    total = len(songs)
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    data["page"] = page

    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_songs = songs[start:end]

    # Matn
    text_parts = [
        f"🔍 <b>\"{query}\"</b> — {total} ta natija topildi\n",
    ]

    for i, song in enumerate(page_songs):
        idx = start + i + 1
        title = song.get("title", "Noma'lum")
        channel = song.get("channel", "")
        duration = song.get("duration", 0)

        if duration:
            mins, secs = divmod(int(duration), 60)
            dur_str = f"{mins}:{secs:02d}"
        else:
            dur_str = "—"

        text_parts.append(f"<b>{idx}.</b> {title}")
        text_parts.append(f"    🎤 {channel} | ⏱ {dur_str}")

    if total_pages > 1:
        text_parts.append(f"\n📄 Sahifa {page + 1}/{total_pages}")

    # Keyboard — raqamli tugmalar 5x2
    builder = InlineKeyboardBuilder()
    for i, song in enumerate(page_songs):
        idx = start + i + 1
        url = song.get("url", "")
        song_hash = hashlib.md5(f"{url}{start+i}".encode()).hexdigest()[:10]
        _search_results[song_hash] = url
        builder.button(
            text=str(idx),
            callback_data=f"song_dl:{song_hash}",
        )

    # 5 ta qatorda joylashtirish (5x2 grid)
    builder.adjust(5)

    # Navigatsiya tugmalari
    nav_builder = InlineKeyboardBuilder()
    if page > 0:
        nav_builder.button(text="⬅️", callback_data=f"spage:{search_id}:{page - 1}")
    else:
        nav_builder.button(text="⬅️", callback_data="noop")

    nav_builder.button(text="❌", callback_data="cancel")

    if page < total_pages - 1:
        nav_builder.button(text="➡️", callback_data=f"spage:{search_id}:{page + 1}")
    else:
        nav_builder.button(text="➡️", callback_data="noop")

    nav_builder.adjust(3)

    # Ikki builder ni birlashtirish
    builder.attach(nav_builder)

    return "\n".join(text_parts), builder


async def _handle_music_search(
    message: Message,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    stats_service: StatsService | None,
    query: str,
) -> None:
    """Foydalanuvchi yozgan matn bo'yicha YouTube'dan musiqa qidirish."""
    if stats_service:
        stats_service.increment_searches(message.from_user.id)

    status_msg = await message.reply(
        f"🔍 <b>\"{query}\" qidirilmoqda...</b>",
        parse_mode="HTML",
    )

    songs = await search_songs(query, limit=50)

    if not songs:
        await status_msg.edit_text(
            f"❌ <b>Natija topilmadi</b>\n\n"
            f"\"{query}\" bo'yicha hech narsa topilmadi.",
            parse_mode="HTML",
        )
        return

    # Natijalarni saqlash
    search_id = hashlib.md5(f"{query}{time.time()}".encode()).hexdigest()[:10]
    _search_pages[search_id] = {
        "query": query,
        "songs": songs,
        "page": 0,
    }

    text, builder = _build_search_page(search_id, page=0)

    await status_msg.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )


# =========================================================
#  Sahifa almashtirish (pagination)
# =========================================================

@router.callback_query(F.data.startswith("spage:"))
async def handle_search_page(callback: CallbackQuery) -> None:
    """Qidiruv natijalari sahifasini almashtirish."""
    parts = callback.data.split(":")
    search_id = parts[1]
    page = int(parts[2])

    if search_id not in _search_pages:
        await callback.answer("❌ Natija eskirgan. Qaytadan qidiring.", show_alert=True)
        return

    text, builder = _build_search_page(search_id, page)

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    """Bo'sh tugma — hech narsa qilmaydi."""
    await callback.answer()


@router.callback_query(F.data.startswith("song_dl:"))
async def handle_song_download(
    callback: CallbackQuery,
    bot: Bot,
    downloader: Downloader,
    stats_service: StatsService = None,
) -> None:
    """Qidiruv natijasidan musiqa yuklab olish."""
    song_hash = callback.data.split(":")[1]
    url = _search_results.get(song_hash)

    if not url:
        await callback.answer(
            "❌ Natija eskirgan. Qaytadan qidiring.", show_alert=True
        )
        return

    await callback.answer("🎵 Musiqa yuklab olinmoqda!")

    status_msg = await callback.message.reply(
        "🎵 <b>Yuklab olinmoqda...</b>\n\n"
        "⚡ YouTube'dan MP3 yuklanmoqda...",
        parse_mode="HTML",
    )

    downloaded_path = None
    try:
        start_time = time.time()

        # Qo'shiqni qidirib yuklab olish
        downloaded_path, song_title = await search_and_download_song(
            query=url,  # to'g'ridan-to'g'ri YouTube URL
            temp_dir=downloader.temp_dir,
        )

        if not downloaded_path or not os.path.exists(downloaded_path):
            await status_msg.edit_text(
                "❌ <b>Yuklab olishda xato</b>\n\n"
                "Qaytadan urinib ko'ring.",
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
            f"📤 <b>Telegramga yuborilmoqda...</b>\n📁 {size_str}",
            parse_mode="HTML",
        )

        input_file = FSInputFile(downloaded_path)
        await bot.send_audio(
            chat_id=callback.message.chat.id,
            audio=input_file,
            caption=(
                f"🎵 <b>{song_title}</b>\n"
                f"⚡ {download_time:.1f}s da yuklandi"
            ),
            parse_mode="HTML",
            title=song_title,
        )

        # Stats: qidiruv orqali yuklangan — stats'ga qo'shish
        if stats_service and callback.from_user:
            stats_service.increment_downloads(callback.from_user.id)

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Song download xatosi: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Xato:</b> {str(e)[:200]}",
            parse_mode="HTML",
        )
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
            except Exception:
                pass


# =========================================================
#  Video dan musiqa ajratib olish
# =========================================================

@router.callback_query(F.data.startswith("ext_audio:"))
async def handle_extract_music(
    callback: CallbackQuery,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    config: Config = None,
    stats_service: StatsService = None,
) -> None:
    """Video da ishlatilgan musiqani Shazam orqali aniqlash va yuklab berish."""
    url_hash = callback.data.split(":")[1]

    # Video xabardan file_id olish
    video_file_id = None
    if callback.message and callback.message.video:
        video_file_id = callback.message.video.file_id

    if not video_file_id:
        await callback.answer(
            "❌ Video topilmadi. Qaytadan yuboring.", show_alert=True
        )
        return

    await callback.answer("🎵 Musiqa aniqlanmoqda...")

    # Video xabardan tugmani olib tashlash
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Status xabar
    status_msg = await bot.send_message(
        chat_id=callback.message.chat.id,
        text="🔍 <b>Musiqa aniqlanmoqda...</b>\n\n"
             "🎵 Shazam orqali videodagi qo'shiq qidirilmoqda...",
        parse_mode="HTML",
    )

    temp_path = None
    downloaded_path = None
    try:
        # 1. Shazam orqali musiqani aniqlash
        result, temp_path = await recognize_from_telegram_file(
            bot=bot,
            file_id=video_file_id,
            temp_dir=downloader.temp_dir,
        )

        if not result.found:
            # Shazam topa olmadi — oddiy audio ajratish
            await status_msg.edit_text(
                "⚠️ <b>Shazam qo'shiqni aniqlay olmadi</b>\n\n"
                "📥 Video dan audio ajratib berilmoqda...",
                parse_mode="HTML",
            )

            url = _get_url(url_hash)
            if url:
                await _download_and_send_ext_audio(
                    status_msg=status_msg,
                    bot=bot,
                    downloader=downloader,
                    cache_service=cache_service,
                    url=url,
                    audio_format=AudioFormat.MP3,
                    quality_str="mp3",
                    config=config,
                )
            else:
                await status_msg.edit_text(
                    "❌ <b>Qo'shiq aniqlanmadi va havola eskirgan.</b>\n\n"
                    "Qaytadan havola yuboring.",
                    parse_mode="HTML",
                )
            return

        # 2. Qo'shiq topildi — foydalanuvchiga ko'rsatish
        title = result.title
        artist = result.artist

        await status_msg.edit_text(
            f"🎵 <b>Topildi!</b>\n\n"
            f"🎤 <b>{artist}</b> — <b>{title}</b>\n"
            f"{'💿 ' + result.album + chr(10) if result.album else ''}"
            f"\n📥 YouTube'dan yuklab olinmoqda...",
            parse_mode="HTML",
        )

        # 3. YouTube'dan qidirish va yuklab olish
        start_time = time.time()
        downloaded_path, song_title = await search_and_download_song(
            query=f"{artist} - {title}",
            temp_dir=downloader.temp_dir,
        )

        if not downloaded_path or not os.path.exists(downloaded_path):
            await status_msg.edit_text(
                f"❌ <b>Qo'shiq topilmadi</b>\n\n"
                f"🎵 <b>{artist} — {title}</b> YouTube'dan topilmadi.\n"
                f"Lekin qo'shiq nomi: <code>{artist} - {title}</code>",
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

        # 4. Telegramga yuborish
        input_file = FSInputFile(downloaded_path)
        caption = (
            f"🎵 <b>{title}</b>\n"
            f"🎤 {artist}\n"
            f"⚡ {download_time:.1f}s da yuklandi"
        )
        if result.album:
            caption += f"\n💿 {result.album}"

        await bot.send_audio(
            chat_id=callback.message.chat.id,
            audio=input_file,
            caption=caption,
            parse_mode="HTML",
            title=f"{artist} - {title}",
            performer=artist,
        )

        # Stats: muvaffaqiyatli yuklangan
        if stats_service and callback.from_user:
            stats_service.increment_downloads(callback.from_user.id)

        # Status xabarni o'chirish
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"ext_audio Shazam xatosi: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Xato yuz berdi:</b> {str(e)[:200]}",
            parse_mode="HTML",
        )
    finally:
        # Temp fayllarni o'chirish
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if downloaded_path and os.path.exists(downloaded_path):
            try:
                os.remove(downloaded_path)
            except Exception:
                pass


# =========================================================
#  Video sifatini tanlash
# =========================================================

@router.callback_query(F.data.startswith("quality:"))
async def handle_quality_select(callback: CallbackQuery) -> None:
    """Video sifatini tanlash keyboard-i."""
    url_hash = callback.data.split(":")[1]

    await callback.message.edit_text(
        "🎬 <b>Video sifatini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_quality_keyboard(url_hash),
    )
    await callback.answer()


# =========================================================
#  Orqaga qaytish
# =========================================================

@router.callback_query(F.data.startswith("back:"))
async def handle_back(callback: CallbackQuery) -> None:
    """Asosiy format tanlash keyboard-iga qaytish."""
    url_hash = callback.data.split(":")[1]

    await callback.message.edit_text(
        "📥 <b>Nima yuklab olmoqchisiz?</b>",
        parse_mode="HTML",
        reply_markup=get_format_keyboard(url_hash),
    )
    await callback.answer()


# =========================================================
#  Video yuklash
# =========================================================

@router.callback_query(F.data.startswith("dl:video:"))
async def handle_video_download(
    callback: CallbackQuery,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    stats_service: StatsService = None,
    config: Config = None,
) -> None:
    """Video yuklab olish va yuborish."""
    parts = callback.data.split(":")
    quality_str = parts[2]
    url_hash = parts[3]

    url = _get_url(url_hash)
    if not url:
        await callback.answer("❌ Havola eskirgan. Qaytadan yuboring.", show_alert=True)
        return

    # Quality mapping
    quality_map = {
        "360": VideoQuality.Q360,
        "480": VideoQuality.Q480,
        "720": VideoQuality.Q720,
        "1080": VideoQuality.Q1080,
        "best": VideoQuality.BEST,
    }
    quality = quality_map.get(quality_str, VideoQuality.BEST)

    await callback.answer("⚡ Yuklab olish boshlandi!")

    # Cache tekshirish
    cached = await cache_service.get_file_id(url, "video", quality_str)
    if cached:
        await _send_cached(callback.message, bot, cached, "video")
        return

    # Yuklab olish (yt-dlp)
    await _download_and_send(
        message=callback.message,
        bot=bot,
        downloader=downloader,
        cache_service=cache_service,
        url=url,
        media_type=MediaType.VIDEO,
        quality=quality,
        quality_str=quality_str,
        url_hash=url_hash,
        stats_service=stats_service,
        config=config,
        user_id_for_stats=callback.from_user.id if callback.from_user else None,
    )


# =========================================================
#  Audio yuklash (MP3/Opus)
# =========================================================

@router.callback_query(F.data.startswith("audio:"))
async def handle_audio_download(
    callback: CallbackQuery,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    stats_service: StatsService = None,
    config: Config = None,
) -> None:
    """Audio yuklab olish va yuborish."""
    parts = callback.data.split(":")
    audio_fmt = parts[1]
    url_hash = parts[2]

    url = _get_url(url_hash)
    if not url:
        await callback.answer("❌ Havola eskirgan. Qaytadan yuboring.", show_alert=True)
        return

    format_map = {
        "mp3": AudioFormat.MP3,
        "opus": AudioFormat.OPUS,
        "m4a": AudioFormat.M4A,
    }
    audio_format = format_map.get(audio_fmt, AudioFormat.MP3)

    await callback.answer("🎵 Musiqa yuklab olinmoqda!")

    # Cache tekshirish
    cached = await cache_service.get_file_id(url, "audio", audio_fmt)
    if cached:
        await _send_cached(callback.message, bot, cached, "audio")
        return

    # Yuklab olish (yt-dlp)
    await _download_and_send(
        message=callback.message,
        bot=bot,
        downloader=downloader,
        cache_service=cache_service,
        url=url,
        media_type=MediaType.AUDIO,
        audio_format=audio_format,
        quality_str=audio_fmt,
        stats_service=stats_service,
        config=config,
        user_id_for_stats=callback.from_user.id if callback.from_user else None,
    )


# =========================================================
#  Bekor qilish
# =========================================================

@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery) -> None:
    """Yuklab olishni bekor qilish."""
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()


# =========================================================
#  Ichki funksiyalar
# =========================================================

async def _send_cached(
    message: Message,
    bot: Bot,
    cached: dict,
    file_type: str,
) -> None:
    """Cache-dan file_id orqali darhol yuborish."""
    file_id = cached.get("file_id", "")
    title = cached.get("title", "Media")
    # Haqiqiy saqlangan tur (video/audio/document)
    actual_type = cached.get("file_type", file_type)

    try:
        await message.edit_text(
            "⚡ <b>Cache-dan yuborilmoqda...</b> (0 soniya!)",
            parse_mode="HTML",
        )
        if actual_type == "video":
            await bot.send_video(
                chat_id=message.chat.id,
                video=file_id,
                caption=f"🎬 {title}\n⚡ Cache-dan yuborildi",
            )
        elif actual_type == "audio":
            await bot.send_audio(
                chat_id=message.chat.id,
                audio=file_id,
                caption=f"🎵 {title}\n⚡ Cache-dan yuborildi",
            )
        elif actual_type == "voice":
            await bot.send_voice(
                chat_id=message.chat.id,
                voice=file_id,
                caption=f"🎵 {title}\n⚡ Cache-dan yuborildi",
            )
        else:
            # Document va boshqalar
            await bot.send_document(
                chat_id=message.chat.id,
                document=file_id,
                caption=f"📎 {title}\n⚡ Cache-dan yuborildi",
            )

        await message.delete()
    except Exception as e:
        logger.error(f"Cache-dan yuborishda xato: {e}")
        await message.edit_text("❌ Xato yuz berdi. Qaytadan urinib ko'ring.")


async def _download_and_send(
    message: Message,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    url: str,
    media_type: MediaType,
    quality: VideoQuality = VideoQuality.BEST,
    audio_format: AudioFormat = AudioFormat.MP3,
    quality_str: str = "",
    url_hash: str = "",
    stats_service: StatsService | None = None,
    config: Config | None = None,
    user_id_for_stats: int | None = None,
) -> None:
    """Video/audio yuklab olish va Telegramga yuborish."""
    user_id = message.chat.id
    file_limit = _file_limit(config)
    max_size = config.download.max_file_size if config else 2_147_483_648

    # Kuzatish uchun: o'zgaruvchilarni oldindan None qilib initsializatsiya qilamiz
    result: DownloadResult | None = None
    compressed_path: str | None = None

    # Foydalanuvchi yuklanishlarini oshirish
    await cache_service.increment_user_downloads(user_id)

    # Status xabar
    status_msg = await message.edit_text(
        "⏳ <b>Yuklab olinmoqda...</b>\n\n"
        "⚡ aria2c 16 ta parallel ulanish bilan yuklamoqda\n"
        "📊 0%",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard(),
    )

    try:
        # Typing action ko'rsatish
        if media_type == MediaType.VIDEO:
            await bot.send_chat_action(user_id, ChatAction.UPLOAD_VIDEO)
        else:
            await bot.send_chat_action(user_id, ChatAction.UPLOAD_VOICE)

        # yt-dlp + aria2c bilan yuklab olish
        start_time = time.time()
        result: DownloadResult = await downloader.download(
            url=url,
            media_type=media_type,
            quality=quality,
            audio_format=audio_format,
        )

        if not result.success:
            await status_msg.edit_text(
                f"❌ <b>Xato:</b> {result.error_message}\n\n"
                f"Qaytadan urinib ko'ring yoki boshqa havola yuboring.",
                parse_mode="HTML",
            )
            return

        download_time = time.time() - start_time

        # Video uchun h264 codec ta'minlash (ensure_h264 ichida ffprobe tekshiradi)
        if media_type == MediaType.VIDEO and result.file_path:
            new_path = await ensure_h264(result.file_path)
            if new_path != result.file_path:
                await status_msg.edit_text(
                    "🔄 <b>Video formatga moslashtirildi</b>",
                    parse_mode="HTML",
                )
                result.file_path = new_path
                result.filesize = os.path.getsize(new_path) if os.path.exists(new_path) else 0

        # Fayl hajmini tekshirish
        if result.filesize > 2_147_483_648:  # 2GB
            await status_msg.edit_text(
                "❌ <b>Fayl juda katta!</b>\n\n"
                f"Hajmi: {_format_size(result.filesize)}\n"
                f"Maksimal: 2 GB",
                parse_mode="HTML",
            )
            await downloader.cleanup(result.file_path)
            return

        # 50MB dan katta bo'lsa — ffmpeg bilan siqish
        compressed_path = None
        if result.filesize > file_limit:
            await status_msg.edit_text(
                f"🗜 <b>Fayl katta ({_format_size(result.filesize)}), siqilmoqda...</b>\n\n"
                f"⏱ Yuklab olish: {download_time:.1f}s\n"
                f"📦 ffmpeg bilan 50MB gacha siqilmoqda...",
                parse_mode="HTML",
            )

            compressed_path = await compress_video(
                input_path=result.file_path,
                target_size_mb=49.0,
            )

            if compressed_path and os.path.exists(compressed_path):
                old_size = result.filesize
                result.file_path = compressed_path
                result.filesize = os.path.getsize(compressed_path)
                logger.info(
                    f"Video siqildi: {_format_size(old_size)} → {_format_size(result.filesize)}"
                )
            else:
                await status_msg.edit_text(
                    "❌ <b>Fayl juda katta!</b>\n\n"
                    f"Hajmi: {_format_size(result.filesize)}\n"
                    f"Telegram limiti: 50 MB\n\n"
                    f"💡 Pastroq sifat (360p/480p) tanlang.",
                    parse_mode="HTML",
                )
                await downloader.cleanup(result.file_path)
                return

        # Status yangilash
        await status_msg.edit_text(
            f"📤 <b>Telegramga yuborilmoqda...</b>\n\n"
            f"📁 {_format_size(result.filesize)} | "
            f"⏱ {download_time:.1f}s da yuklandi",
            parse_mode="HTML",
        )

        # Telegramga yuborish
        sent_message = await _send_file(
            bot=bot,
            chat_id=user_id,
            result=result,
            download_time=download_time,
            url_hash=url_hash,
            file_limit=file_limit,
        )

        # file_id ni cache-ga saqlash (sent type bilan mos)
        if sent_message:
            file_id, actual_type = _extract_file_id(sent_message, media_type)
            if file_id:
                await cache_service.set_file_id(
                    url=url,
                    media_type=media_type.value,
                    quality=quality_str,
                    file_id=file_id,
                    title=result.title,
                    duration=result.duration,
                    file_type=actual_type,
                )

            # Stats: muvaffaqiyatli yuklangan yozuvni oshirish
            if stats_service and user_id_for_stats:
                stats_service.increment_downloads(user_id_for_stats)

        # Status xabarni o'chirish
        try:
            await status_msg.delete()
        except Exception:
            pass

    except asyncio.CancelledError:
        await status_msg.edit_text("❌ Bekor qilindi.")
    except Exception as e:
        logger.error(f"Download error: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Kutilmagan xato:</b>\n{str(e)[:200]}",
            parse_mode="HTML",
        )
    finally:
        # Vaqtinchalik fayllarni o'chirish
        if result and result.file_path:
            await downloader.cleanup(result.file_path)
        if compressed_path:
            try:
                if os.path.exists(compressed_path):
                    os.remove(compressed_path)
            except Exception:
                pass
        # Foydalanuvchi yuklanishlarini kamaytirish
        await cache_service.decrement_user_downloads(user_id)


async def _send_file(
    bot: Bot,
    chat_id: int,
    result: DownloadResult,
    download_time: float,
    url_hash: str = "",
    file_limit: int = TELEGRAM_FILE_LIMIT_DEFAULT,
) -> Message | None:
    """Faylni Telegramga yuborish."""
    if not os.path.exists(result.file_path):
        logger.error(f"Fayl topilmadi: {result.file_path}")
        return None

    duration_str = _format_duration(result.duration)
    size_str = _format_size(result.filesize)

    # Video uchun musiqa ajratish tugmasi
    reply_markup = None
    if result.media_type == MediaType.VIDEO and url_hash:
        kb = InlineKeyboardBuilder()
        kb.button(
            text="🎵 Musiqani yuklab olish",
            callback_data=f"ext_audio:{url_hash}",
        )
        reply_markup = kb.as_markup()

    try:
        input_file = FSInputFile(result.file_path)

        if result.media_type == MediaType.VIDEO:
            caption = (
                f"🎬 <b>{result.title}</b>\n"
                f"{'⏱ ' + duration_str + ' | ' if duration_str else ''}"
                f"📁 {size_str} | "
                f"⚡ {download_time:.1f}s"
            )
            sent = await bot.send_video(
                chat_id=chat_id,
                video=input_file,
                caption=caption,
                parse_mode="HTML",
                duration=int(result.duration) if result.duration else None,
                width=result.width,
                height=result.height,
                supports_streaming=True,
                reply_markup=reply_markup,
            )
        else:
            caption = (
                f"🎵 <b>{result.title}</b>\n"
                f"{'⏱ ' + duration_str + ' | ' if duration_str else ''}"
                f"📁 {size_str} | "
                f"⚡ {download_time:.1f}s"
            )
            sent = await bot.send_audio(
                chat_id=chat_id,
                audio=input_file,
                caption=caption,
                parse_mode="HTML",
                duration=int(result.duration) if result.duration else None,
                title=result.title,
            )

        return sent

    except Exception as e:
        logger.error(f"Telegram yuborishda xato: {e}")

        # Agar video hajmi katta bo'lsa, document sifatida yuborish
        if result.filesize > file_limit:
            try:
                input_file = FSInputFile(result.file_path)
                sent = await bot.send_document(
                    chat_id=chat_id,
                    document=input_file,
                    caption=f"📎 {result.title}\n⚡ {download_time:.1f}s",
                    parse_mode="HTML",
                )
                return sent
            except Exception as e2:
                logger.error(f"Document yuborishda ham xato: {e2}")

        return None


def _extract_file_id(message: Message, media_type: MediaType) -> tuple[str | None, str]:
    """Yuborilgan xabardan (file_id, actual_type) qaytarish.

    actual_type — Telegram turi bo'yicha ('video' | 'audio' | 'document').
    Bu cache HIT paytida to'g'ri send_* chaqirish uchun kerak.
    """
    if message.video:
        return message.video.file_id, "video"
    if message.audio:
        return message.audio.file_id, "audio"
    if message.document:
        return message.document.file_id, "document"
    if message.voice:
        return message.voice.file_id, "voice"
    return None, media_type.value


# =========================================================
#  Video dan audio ajratish (ext_audio) — alohida funksiya
# =========================================================

async def _download_and_send_ext_audio(
    status_msg: Message,
    bot: Bot,
    downloader: Downloader,
    cache_service: CacheService,
    url: str,
    audio_format: AudioFormat = AudioFormat.MP3,
    quality_str: str = "mp3",
    config: Config | None = None,
) -> None:
    """Video URL dan audio ajratib yuklab olish va yuborish (alohida status xabar bilan)."""
    user_id = status_msg.chat.id
    file_limit = _file_limit(config)

    # Kuzatish uchun oldindan init
    result: DownloadResult | None = None

    # Foydalanuvchi yuklanishlarini oshirish
    await cache_service.increment_user_downloads(user_id)

    try:
        # Cache tekshirish
        cached = await cache_service.get_file_id(url, "audio", quality_str)
        if cached:
            await _send_cached(status_msg, bot, cached, "audio")
            return

        await bot.send_chat_action(user_id, ChatAction.UPLOAD_VOICE)

        start_time = time.time()
        result = await downloader.download(
            url=url,
            media_type=MediaType.AUDIO,
            audio_format=audio_format,
        )

        if not result.success:
            await status_msg.edit_text(
                f"❌ <b>Xato:</b> {result.error_message}\n\n"
                f"Qaytadan urinib ko'ring yoki boshqa havola yuboring.",
                parse_mode="HTML",
            )
            return

        download_time = time.time() - start_time

        # Fayl hajmini tekshirish
        if result.filesize > file_limit:
            await status_msg.edit_text(
                "❌ <b>Audio fayl juda katta!</b>\n\n"
                f"Hajmi: {_format_size(result.filesize)}\n"
                f"Telegram limiti: {_format_size(file_limit)}",
                parse_mode="HTML",
            )
            await downloader.cleanup(result.file_path)
            return

        # Status yangilash
        await status_msg.edit_text(
            f"📤 <b>Telegramga yuborilmoqda...</b>\n\n"
            f"📁 {_format_size(result.filesize)} | "
            f"⏱ {download_time:.1f}s da yuklandi",
            parse_mode="HTML",
        )

        # Telegramga yuborish
        sent_message = await _send_file(
            bot=bot,
            chat_id=user_id,
            result=result,
            download_time=download_time,
            file_limit=file_limit,
        )

        # file_id ni cache-ga saqlash
        if sent_message:
            file_id, actual_type = _extract_file_id(sent_message, MediaType.AUDIO)
            if file_id:
                await cache_service.set_file_id(
                    url=url,
                    media_type="audio",
                    quality=quality_str,
                    file_id=file_id,
                    title=result.title,
                    duration=result.duration,
                    file_type=actual_type,
                )

        # Status xabarni o'chirish
        try:
            await status_msg.delete()
        except Exception:
            pass

    except asyncio.CancelledError:
        await status_msg.edit_text("❌ Bekor qilindi.")
    except Exception as e:
        logger.error(f"ext_audio download error: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ <b>Kutilmagan xato:</b>\n{str(e)[:200]}",
            parse_mode="HTML",
        )
    finally:
        if result and result.file_path:
            await downloader.cleanup(result.file_path)
        await cache_service.decrement_user_downloads(user_id)
