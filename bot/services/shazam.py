"""
Shazam Service — musiqani aniqlash (audio recognition).

Foydalanuvchi audio/voice yuborganda yoki video uchun
Shazam orqali qo'shiq nomini aniqlash.
"""

import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass

from shazamio import Shazam

logger = logging.getLogger(__name__)


@dataclass
class ShazamResult:
    """Shazam aniqlash natijasi."""
    found: bool = False
    title: str = ""
    artist: str = ""
    album: str = ""
    year: str = ""
    genre: str = ""
    cover_url: str = ""
    shazam_url: str = ""
    apple_music_url: str = ""
    spotify_url: str = ""
    error_message: str = ""


async def recognize_song(file_path: str) -> ShazamResult:
    """
    Audio fayldan qo'shiqni aniqlash.

    Qo'llab-quvvatlanadigan formatlar: mp3, m4a, wav, ogg, flac, mp4, webm
    """
    if not os.path.exists(file_path):
        return ShazamResult(found=False, error_message="Fayl topilmadi")

    try:
        shazam = Shazam()
        result = await shazam.recognize(file_path)

        if not result or "track" not in result:
            return ShazamResult(
                found=False,
                error_message="Qo'shiq aniqlanmadi. Boshqa qismini yuboring.",
            )

        track = result["track"]

        # Metadata olish
        title = track.get("title", "Noma'lum")
        artist = track.get("subtitle", "Noma'lum")
        album = ""
        year = ""
        genre = ""
        cover_url = ""
        apple_music_url = track.get("url", "")
        shazam_url = track.get("share", {}).get("href", "")
        spotify_url = ""

        # Mavjud bo'lsa metadata sections dan olish
        sections = track.get("sections", [])
        for section in sections:
            if section.get("type") == "SONG":
                metadata_list = section.get("metadata", [])
                for meta in metadata_list:
                    meta_title = meta.get("title", "").lower()
                    meta_text = meta.get("text", "")
                    if "album" in meta_title:
                        album = meta_text
                    elif "year" in meta_title or "released" in meta_title:
                        year = meta_text
                    elif "genre" in meta_title:
                        genre = meta_text

        # Cover image
        images = track.get("images", {})
        cover_url = images.get("coverarthq", images.get("coverart", ""))

        # Spotify/Apple links
        providers = track.get("hub", {}).get("providers", [])
        for provider in providers:
            if provider.get("type") == "SPOTIFY":
                actions = provider.get("actions", [])
                for action in actions:
                    if action.get("type") == "uri":
                        spotify_url = action.get("uri", "")

        return ShazamResult(
            found=True,
            title=title,
            artist=artist,
            album=album,
            year=year,
            genre=genre,
            cover_url=cover_url,
            shazam_url=shazam_url,
            apple_music_url=apple_music_url,
            spotify_url=spotify_url,
        )

    except Exception as e:
        logger.error(f"Shazam xatosi: {e}", exc_info=True)
        return ShazamResult(
            found=False,
            error_message=f"Aniqlashda xato: {str(e)[:200]}",
        )


async def recognize_from_telegram_file(
    bot,
    file_id: str,
    temp_dir: str = "./tmp",
) -> tuple[ShazamResult, str]:
    """
    Telegram file_id dan faylni yuklab, Shazam orqali aniqlash.

    Returns: (ShazamResult, temp_file_path)
    """
    try:
        # Telegram serverdan faylni yuklab olish
        file = await bot.get_file(file_id)
        file_ext = os.path.splitext(file.file_path)[1] if file.file_path else ".ogg"

        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"shazam_{file_id[:20]}{file_ext}")

        await bot.download_file(file.file_path, temp_path)

        # Shazam bilan aniqlash
        result = await recognize_song(temp_path)

        return result, temp_path

    except Exception as e:
        logger.error(f"Telegram file download xatosi: {e}")
        return ShazamResult(found=False, error_message=str(e)[:200]), ""


def _sync_search_download(query: str, temp_dir: str) -> dict:
    """
    YouTube'dan qo'shiqni qidirib yuklab olish (sinxron).
    ProcessPoolExecutor ichida ishlatiladi.
    """
    import yt_dlp

    try:
        os.makedirs(temp_dir, exist_ok=True)

        opts = {
            "format": "bestaudio[ext=m4a]/bestaudio[ext=opus]/bestaudio/best",
            "paths": {"home": temp_dir, "temp": temp_dir},
            "outtmpl": {"default": "shazam_%(id)s.%(ext)s"},
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "nocheckcertificate": True,
            "socket_timeout": 30,
            "retries": 3,
            "default_search": "ytsearch",
            # Railway datacenter IP bot-detection'ni aylantirish:
            # mweb/tv_embedded/ios clientlar cookie talab qilmaydi
            "extractor_args": {
                "youtube": {
                    "player_client": ["mweb", "tv_embedded", "ios", "android_vr"],
                },
            },
            "user_agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "320",
                }
            ],
        }

        # Qidiruv so'rovi turlari \u2014 birin-ketin sinaymiz
        # Em-dash va qavslar YouTube qidiruvni buzadi
        import re as _re
        clean = _re.sub(r"[\u2013\u2014\u2015]", "-", query)  # em/en-dash -> -
        simple = _re.sub(r"\s*\([^)]*\)", "", clean).strip()  # "(Remix)" olib tashlash
        simple = _re.sub(r"\s+", " ", simple)

        candidates = [clean, simple] if simple != clean else [clean]
        # Qo'shimcha: "artist song" (dash'siz)
        dashless = _re.sub(r"\s*[-\u2013\u2014]\s*", " ", simple)
        if dashless not in candidates:
            candidates.append(dashless)

        last_error = "Natija topilmadi"
        with yt_dlp.YoutubeDL(opts) as ydl:
            for q in candidates:
                if not q:
                    continue
                try:
                    info = ydl.extract_info(f"ytsearch:{q}", download=True)
                except Exception as e:
                    last_error = str(e)[:200]
                    continue

                if info is None:
                    continue

                entries = info.get("entries", [])
                if not entries:
                    continue

                entry = entries[0]
                filename = ydl.prepare_filename(entry)

                base = os.path.splitext(filename)[0]
                for ext in ["mp3", "m4a", "opus", "ogg", "wav"]:
                    candidate = f"{base}.{ext}"
                    if os.path.exists(candidate):
                        filename = candidate
                        break

                return {
                    "success": True,
                    "filename": filename,
                    "title": entry.get("title", "Noma'lum"),
                }

            return {"success": False, "error": last_error}

    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


async def search_and_download_song(
    query: str,
    temp_dir: str = "./tmp",
) -> tuple[str | None, str]:
    """
    YouTube'dan qo'shiqni qidirib, MP3 formatda yuklab olish.

    Args:
        query: Qidiruv so'rovi (masalan, "Artist - Song Title")
        temp_dir: Vaqtinchalik fayllar papkasi

    Returns:
        (file_path, title) yoki (None, "") agar topilmasa
    """
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,  # default executor
            _sync_search_download,
            query,
            temp_dir,
        )

        if result.get("success") and result.get("filename"):
            filename = result["filename"]
            if os.path.exists(filename):
                logger.info(
                    f"Shazam download: '{query}' -> {filename} "
                    f"({os.path.getsize(filename) / (1024*1024):.1f}MB)"
                )
                return filename, result.get("title", "")

        error = result.get("error", "Noma'lum xato")
        logger.warning(f"Shazam download topilmadi: '{query}' | {error}")
        return None, ""

    except Exception as e:
        logger.error(f"search_and_download xatosi: {e}")
        return None, ""


# ===========================================================
#  YouTube musiqa qidirish (yuklamasdan — faqat natijalar)
# ===========================================================


def _sync_search_songs(query: str, limit: int = 5) -> list[dict]:
    """YouTube'dan qo'shiqlarni qidirish (sinxron, yuklamasdan)."""
    import yt_dlp

    try:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "default_search": "ytsearch",
            "nocheckcertificate": True,
            "socket_timeout": 15,
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            if not info:
                return []

            entries = info.get("entries", [])
            results = []

            for entry in entries:
                if not entry:
                    continue

                video_id = entry.get("id", "")
                url = entry.get("url", "")
                if not url and video_id:
                    url = f"https://www.youtube.com/watch?v={video_id}"
                elif url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"

                results.append(
                    {
                        "id": video_id,
                        "title": entry.get("title", "Noma'lum"),
                        "url": url,
                        "duration": entry.get("duration", 0),
                        "channel": entry.get(
                            "channel", entry.get("uploader", "")
                        ),
                        "thumbnail": (
                            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                            if video_id
                            else ""
                        ),
                    }
                )

            return results

    except Exception as e:
        logger.error(f"YouTube search xatosi: {e}")
        return []


async def search_songs(query: str, limit: int = 5) -> list[dict]:
    """
    YouTube'dan qo'shiqlarni qidirish (async).

    Returns: [{id, title, url, duration, channel, thumbnail}, ...]
    """
    try:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, _sync_search_songs, query, limit
        )
    except Exception as e:
        logger.error(f"search_songs xatosi: {e}")
        return []
