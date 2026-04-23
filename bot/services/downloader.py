"""
Downloader Service — yt-dlp + fastdl yordamida video/audio yuklab olish.

Tezlik optimizatsiyalari:
- fastdl: 16 ta parallel ulanish, faylni bo'laklarga bo'lib yuklash (3-10x tezroq)
- yt-dlp Python API: subprocess chaqiruvsiz, to'g'ridan-to'g'ri (50-200ms tejash)
- ProcessPoolExecutor: CPU-bound yt-dlp ishlarini alohida jarayonda bajarish
- tmpfs (/dev/shm): RAM diskda vaqtinchalik fayllar (disk I/O yo'q)
"""

import asyncio
import hashlib
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import shutil

import yt_dlp

logger = logging.getLogger(__name__)

# Global thread pool (yt-dlp I/O-bound ishlari uchun — ProcessPool dan tezroq).
# max_workers Downloader tomonidan belgilanadi (max_concurrent bilan mos).
_thread_pool: ThreadPoolExecutor | None = None

# fastdl mavjudligini tekshirish (bir marta)
_fastdl_available: bool | None = None


def is_fastdl_available() -> bool:
    """fastdl o'rnatilganligini tekshirish (cached)."""
    global _fastdl_available
    if _fastdl_available is None:
        _fastdl_available = shutil.which("fastdl") is not None
    return _fastdl_available


def get_thread_pool(max_workers: int = 8) -> ThreadPoolExecutor:
    """Thread pool ni olish yoki yaratish."""
    global _thread_pool
    if _thread_pool is None:
        _thread_pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="ytdlp",
        )
    return _thread_pool


class MediaType(Enum):
    """Yuklab olinadigan media turi."""
    VIDEO = "video"
    AUDIO = "audio"


class VideoQuality(Enum):
    """Video sifati."""
    Q360 = "360"
    Q480 = "480"
    Q720 = "720"
    Q1080 = "1080"
    BEST = "best"


class AudioFormat(Enum):
    """Audio formati."""
    MP3 = "mp3"
    OPUS = "opus"
    M4A = "m4a"


@dataclass
class DownloadProgress:
    """Yuklanish holati."""
    status: str = "preparing"  # preparing, downloading, processing, uploading, done, error
    percent: float = 0.0
    speed: str = ""
    eta: str = ""
    filename: str = ""
    filesize: int = 0
    downloaded: int = 0


@dataclass
class DownloadResult:
    """Yuklab olish natijasi."""
    success: bool = False
    file_path: str = ""
    title: str = ""
    duration: int = 0
    filesize: int = 0
    thumbnail_url: str = ""
    media_type: MediaType = MediaType.VIDEO
    width: int = 0
    height: int = 0
    error_message: str = ""
    download_time: float = 0.0


def _build_fastdl_args(connections: int = 16, split: int = 16, min_split_size: str = "1M") -> list[str]:
    """fastdl tashqi yuklovchi argumentlarini yaratish."""
    return [
        f"-x", str(connections),         # Max connections per server
        f"-s", str(split),               # Number of splits
        f"-k", min_split_size,           # Min split size
        "--file-allocation=none",        # Tez boshlash uchun
        "--optimize-concurrent-downloads=true",
        "--summary-interval=0",          # Progress chiqishini kamaytirish
        "--console-log-level=error",     # Kamroq log
        "--auto-file-renaming=false",
        "--allow-overwrite=true",
    ]


# Platformaga xos User-Agent
_UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
_UA_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_UA_INSTAGRAM_APP = (
    "Instagram 292.0.0.18.109 (iPhone14,3; iOS 17_5; en_US; en; scale=3.00; 1284x2778; 508527186)"
)


def _detect_platform(url: str) -> str:
    u = (url or "").lower()
    if "instagram.com" in u or "instagr.am" in u:
        return "instagram"
    if "tiktok.com" in u:
        return "tiktok"
    if "facebook.com" in u or "fb.watch" in u or "fb.com" in u:
        return "facebook"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "twitter.com" in u or "x.com" in u:
        return "twitter"
    if "snapchat.com" in u:
        return "snapchat"
    if "pinterest." in u or "pin.it" in u:
        return "pinterest"
    if "likee." in u or "like-video.com" in u:
        return "likee"
    return "generic"


def _build_ydl_opts(
    media_type: MediaType,
    quality: VideoQuality = VideoQuality.BEST,
    audio_format: AudioFormat = AudioFormat.MP3,
    temp_dir: str = "./tmp",
    fastdl_connections: int = 16,
    fastdl_split: int = 16,
    fastdl_min_split_size: str = "1M",
    progress_callback: Callable | None = None,
    cookies_file: str = "",
    proxy: str = "",
    url: str = "",
) -> dict[str, Any]:
    """yt-dlp opsiyalarini yaratish."""

    platform = _detect_platform(url)

    # Platformaga ko'ra User-Agent tanlash
    if platform == "instagram":
        user_agent = _UA_IPHONE
    elif platform in ("tiktok", "snapchat", "likee"):
        user_agent = _UA_IPHONE
    else:
        user_agent = _UA_DESKTOP

    # Asosiy opsiyalar
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "no_color": True,
        "paths": {"home": temp_dir, "temp": temp_dir},
        "outtmpl": {"default": "%(id)s_%(epoch)s.%(ext)s"},
        "overwrites": True,
        "noplaylist": True,
        # TLS sertifikat tekshiruvi yoqilgan (MITM himoyasi)
        "nocheckcertificate": False,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "extractor_retries": 5,
        "concurrent_fragment_downloads": 8,
        "sleep_interval_requests": 1,
        "http_headers": {
            "User-Agent": user_agent,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    }

    # Instagram uchun maxsus extractor argumentlari (rate-limit bypass)
    if platform == "instagram":
        opts["extractor_args"] = {
            "instagram": {
                "app_id": ["936619743392459"],  # Instagram Web App ID
            }
        }
        # Instagram agressiv rate-limit qo'yadi — ko'proq kutish
        opts["sleep_interval"] = 2
        opts["max_sleep_interval"] = 5

    # Cookies fayl mavjud bo'lsa qo'shish (Instagram, Facebook va h.k. uchun)
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
        logger.debug(f"Cookies fayl ishlatilmoqda: {cookies_file}")

    # Proxy (Cloudflare WARP yoki boshqa SOCKS5/HTTP proxy)
    if proxy:
        opts["proxy"] = proxy
        logger.debug(f"Proxy ishlatilmoqda: {proxy}")

    # fastdl faqat o'rnatilgan bo'lsa ishlatiladi
    if is_fastdl_available():
        opts["external_downloader"] = "fastdl"
        opts["external_downloader_args"] = {
            "fastdl": _build_fastdl_args(fastdl_connections, fastdl_split, fastdl_min_split_size),
        }

    if media_type == MediaType.VIDEO:
        # Video format — birlashgan mp4 afzal (merge/encode kerak emas = tez!)
        # Faqat birlashgan topilmasa, bestvideo+bestaudio ishlatiladi
        if quality == VideoQuality.BEST:
            opts["format"] = (
                "best[ext=mp4][vcodec^=avc1][height<=1080]/"
                "best[ext=mp4][height<=1080]/"
                "bestvideo[vcodec^=avc1][height<=1080]+bestaudio[acodec^=mp4a]/"
                "bestvideo[vcodec^=avc1][height<=1080]+bestaudio/"
                "bestvideo[height<=1080]+bestaudio/"
                "best[height<=1080]/best"
            )
        else:
            height = quality.value
            opts["format"] = (
                f"best[ext=mp4][vcodec^=avc1][height<={height}]/"
                f"best[ext=mp4][height<={height}]/"
                f"bestvideo[vcodec^=avc1][height<={height}]+bestaudio[acodec^=mp4a]/"
                f"bestvideo[vcodec^=avc1][height<={height}]+bestaudio/"
                f"bestvideo[height<={height}]+bestaudio/"
                f"best[height<={height}]/best"
            )

        # MP4 formatga birlashtirish (faqat separate streams uchun)
        opts["merge_output_format"] = "mp4"
        opts["postprocessors"] = [
            {
                "key": "FFmpegVideoRemuxer",
                "preferedformat": "mp4",
            }
        ]
        # Merge bo'lganda codec copy ishlatish (encode emas = tez!)
        opts["postprocessor_args"] = {
            "merger": ["-c", "copy", "-movflags", "+faststart"]
        }

    elif media_type == MediaType.AUDIO:
        # Audio — to'g'ridan-to'g'ri audio stream yuklash (video yuklamaydi!)
        opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=opus]/bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format.value,
                "preferredquality": "320" if audio_format == AudioFormat.MP3 else "128",
            }
        ]

    # Progress hook
    if progress_callback:
        opts["progress_hooks"] = [progress_callback]

    return opts


def _sync_download(
    url: str,
    opts: dict[str, Any],
) -> dict[str, Any]:
    """
    Sinxron yuklab olish funksiyasi.
    ProcessPoolExecutor ichida ishlatiladi.
    """
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return {"success": False, "error": "Video ma'lumotlari olinmadi"}
            return {
                "success": True,
                "title": info.get("title", "Nomsiz"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "filename": ydl.prepare_filename(info),
                "ext": info.get("ext", "mp4"),
                "id": info.get("id", ""),
                "filesize_approx": info.get("filesize_approx", 0),
            }
    except yt_dlp.utils.DownloadError as e:
        return {"success": False, "error": f"Yuklab olishda xato: {str(e)[:200]}"}
    except Exception as e:
        return {"success": False, "error": f"Kutilmagan xato: {str(e)[:200]}"}


def _sync_extract_info(url: str, opts: dict[str, Any]) -> dict[str, Any]:
    """Video ma'lumotlarini yuklamasdan olish (sinxron)."""
    try:
        extract_opts = {**opts, "skip_download": True, "quiet": True}
        # Extract info uchun fastdl kerak emas
        extract_opts.pop("external_downloader", None)
        extract_opts.pop("external_downloader_args", None)

        with yt_dlp.YoutubeDL(extract_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                return {"success": False, "error": "Ma'lumot olinmadi"}
            return {
                "success": True,
                "title": info.get("title", "Nomsiz"),
                "duration": info.get("duration", 0),
                "thumbnail": info.get("thumbnail", ""),
                "formats_count": len(info.get("formats", [])),
                "description": (info.get("description", "") or "")[:200],
            }
    except Exception as e:
        return {"success": False, "error": str(e)[:200]}


class Downloader:
    """
    Asosiy yuklovchi sinf.

    yt-dlp Python API + fastdl tashqi yuklovchi yordamida
    ijtimoiy tarmoqlardan video/audio yuklab olish.
    """

    def __init__(
        self,
        temp_dir: str = "./tmp",
        fastdl_connections: int = 16,
        fastdl_split: int = 16,
        fastdl_min_split_size: str = "1M",
        max_concurrent: int = 20,
        cookies_file: str = "",
        proxy: str = "",
    ):
        self.temp_dir = temp_dir
        self.fastdl_connections = fastdl_connections
        self.fastdl_split = fastdl_split
        self.fastdl_min_split_size = fastdl_min_split_size
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self.max_concurrent = max_concurrent
        self.cookies_file = cookies_file
        self.proxy = proxy

        # Temp directory yaratish
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        # Thread pool'ni max_concurrent ga mos o'lchamda ishga tushirish
        get_thread_pool(max_workers=max_concurrent)

    async def get_info(self, url: str) -> dict[str, Any]:
        """Video ma'lumotlarini yuklamasdan olish (async)."""
        opts = _build_ydl_opts(
            MediaType.VIDEO,
            temp_dir=self.temp_dir,
            cookies_file=self.cookies_file,
            proxy=self.proxy,
            url=url,
        )
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            get_thread_pool(),
            _sync_extract_info,
            url,
            opts,
        )
        return result

    async def download(
        self,
        url: str,
        media_type: MediaType = MediaType.VIDEO,
        quality: VideoQuality = VideoQuality.BEST,
        audio_format: AudioFormat = AudioFormat.MP3,
    ) -> DownloadResult:
        """
        Video yoki audio yuklab olish (async).

        fastdl bilan 16 ta parallel ulanish orqali 3-10x tezroq.
        """
        start_time = time.time()

        async with self._semaphore:
            opts = _build_ydl_opts(
                media_type=media_type,
                quality=quality,
                audio_format=audio_format,
                temp_dir=self.temp_dir,
                fastdl_connections=self.fastdl_connections,
                fastdl_split=self.fastdl_split,
                fastdl_min_split_size=self.fastdl_min_split_size,
                cookies_file=self.cookies_file,
                proxy=self.proxy,
                url=url,
            )

            logger.info(f"Yuklab olish boshlandi: {url} | type={media_type.value} | quality={quality.value}")

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                get_thread_pool(),
                _sync_download,
                url,
                opts,
            )

        download_time = time.time() - start_time

        if not result.get("success"):
            logger.error(f"Yuklab olish xatosi: {url} | {result.get('error')}")
            return DownloadResult(
                success=False,
                error_message=result.get("error", "Noma'lum xato"),
                download_time=download_time,
            )

        # Fayl yo'lini aniqlash
        filename = result.get("filename", "")
        if media_type == MediaType.AUDIO:
            # Audio postprocessor fayl kengaytmasini o'zgartiradi
            base = os.path.splitext(filename)[0]
            audio_file = f"{base}.{audio_format.value}"
            if os.path.exists(audio_file):
                filename = audio_file
            else:
                # Boshqa kengaytmalarni tekshirish
                for ext in ["mp3", "m4a", "opus", "ogg", "wav"]:
                    candidate = f"{base}.{ext}"
                    if os.path.exists(candidate):
                        filename = candidate
                        break

        # Fayl hajmini aniqlash
        filesize = 0
        if os.path.exists(filename):
            filesize = os.path.getsize(filename)

        logger.info(
            f"Yuklab olish tugadi: {result.get('title')} | "
            f"{filesize / 1024 / 1024:.1f}MB | {download_time:.1f}s"
        )

        return DownloadResult(
            success=True,
            file_path=filename,
            title=result.get("title", "Nomsiz"),
            duration=result.get("duration", 0),
            filesize=filesize,
            thumbnail_url=result.get("thumbnail", ""),
            media_type=media_type,
            width=result.get("width", 0),
            height=result.get("height", 0),
            download_time=download_time,
        )

    async def cleanup(self, file_path: str) -> None:
        """Vaqtinchalik faylni o'chirish."""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Fayl o'chirildi: {file_path}")
        except OSError as e:
            logger.warning(f"Fayl o'chirishda xato: {file_path} | {e}")


def generate_cache_key(url: str, media_type: str, quality: str = "") -> str:
    """URL va format asosida cache kalitini yaratish."""
    raw = f"{url}:{media_type}:{quality}"
    return f"media:{hashlib.sha256(raw.encode()).hexdigest()}"
