"""
Audio Extractor — videolardan musiqani ajratib olish.

Eng tez usullar (tartibi bo'yicha):
1. bestaudio — to'g'ridan-to'g'ri audio stream (video yuklamaydi, 10x kam data)
2. codec copy remux — qayta encode qilmasdan (deyarli bir zumda)
3. ffmpeg transcode — faqat format o'zgartirish kerak bo'lganda
"""

import asyncio
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    """Audio ajratish natijasi."""
    success: bool = False
    file_path: str = ""
    format: str = "mp3"
    duration: int = 0
    filesize: int = 0
    error_message: str = ""


async def get_video_codec(file_path: str) -> str | None:
    """ffprobe bilan video codec aniqlash."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name",
            "-of", "json",
            file_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()
        if process.returncode == 0 and stdout:
            data = json.loads(stdout.decode())
            streams = data.get("streams", [])
            if streams:
                return streams[0].get("codec_name")
    except Exception as e:
        logger.warning(f"ffprobe xatosi: {e}")
    return None


async def ensure_h264(file_path: str) -> str:
    """
    Video faylni Telegram uchun h264+aac formatga o'tkazish.

    Agar allaqachon h264 bo'lsa — o'zgartirmaydi (tez).
    Agar VP9/HEVC/AV1 bo'lsa — ffmpeg bilan qayta encode qiladi.
    """
    if not os.path.exists(file_path):
        return file_path

    codec = await get_video_codec(file_path)
    logger.info(f"Video codec: {codec} | {file_path}")

    # h264 allaqachon bo'lsa — hech narsa qilmaymiz
    if codec and codec.lower() in ("h264", "avc"):
        return file_path

    # Non-h264 codec — qayta encode qilish
    logger.info(f"Video h264 ga convert qilinmoqda (hozirgi: {codec})...")

    base = os.path.splitext(file_path)[0]
    output_path = f"{base}_h264.mp4"

    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", file_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-threads", "0",
            output_path,
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"h264 convert xatosi: {stderr.decode()[:300]}")
            return file_path  # Original faylni qaytaramiz

        if os.path.exists(output_path):
            new_size = os.path.getsize(output_path)
            old_size = os.path.getsize(file_path)
            logger.info(
                f"Video h264 ga convert qilindi: "
                f"{old_size / (1024*1024):.1f}MB → {new_size / (1024*1024):.1f}MB"
            )
            # Original faylni o'chirish
            try:
                os.remove(file_path)
            except Exception:
                pass
            return output_path

        return file_path

    except Exception as e:
        logger.error(f"h264 convert xatosi: {e}")
        return file_path


async def extract_audio_from_file(
    input_path: str,
    output_format: str = "mp3",
    bitrate: str = "320k",
) -> AudioResult:
    """
    Mavjud video fayldan audio ajratib olish.

    ffmpeg -codec copy imkon qadar ishlatiladi (qayta encode yo'q = tez).
    """
    if not os.path.exists(input_path):
        return AudioResult(success=False, error_message="Kirish fayli topilmadi")

    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_audio.{output_format}"

    try:
        # Birinchi, codec copy bilan sinab ko'ramiz (eng tez usul)
        if output_format in ("m4a", "aac"):
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vn",              # Video yo'q
                "-acodec", "copy",  # Audio codec o'zgarmaydi
                output_path,
            ]
        elif output_format == "opus":
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vn",
                "-acodec", "libopus",
                "-b:a", "128k",
                "-vbr", "on",
                "-threads", "0",
                output_path,
            ]
        else:
            # MP3 — eng universal format
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vn",
                "-acodec", "libmp3lame",
                "-b:a", bitrate,
                "-threads", "0",
                output_path,
            ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"ffmpeg xatosi: {stderr.decode()[:300]}")
            return AudioResult(
                success=False,
                error_message="Audio ajratishda xato yuz berdi",
            )

        filesize = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return AudioResult(
            success=True,
            file_path=output_path,
            format=output_format,
            filesize=filesize,
        )

    except Exception as e:
        logger.error(f"Audio extract xatosi: {e}")
        return AudioResult(success=False, error_message=str(e)[:200])


async def get_audio_duration(file_path: str) -> int:
    """ffprobe yordamida audio davomiyligini olish (soniyalarda)."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await process.communicate()

        if process.returncode == 0 and stdout:
            return int(float(stdout.decode().strip()))
    except Exception:
        pass
    return 0


async def compress_video(
    input_path: str,
    target_size_mb: float = 49.0,
) -> str | None:
    """
    Video faylni ffmpeg bilan siqish.
    target_size_mb dan kichik qilishga harakat qiladi.
    Muvaffaqiyatli bo'lsa — siqilgan fayl yo'lini qaytaradi.
    """
    if not os.path.exists(input_path):
        return None

    # Avval video davomiyligini aniqlash
    duration = await get_audio_duration(input_path)
    if duration <= 0:
        duration = 300  # fallback: 5 daqiqa

    # Target bitrate hisoblash (bit/s)
    # target_size (bytes) = bitrate (bit/s) * duration (s) / 8
    # Audio uchun ~128kbps ajratamiz
    target_bytes = target_size_mb * 1024 * 1024
    audio_bitrate = 128_000  # 128 kbps
    video_bitrate = int((target_bytes * 8 / duration) - audio_bitrate)

    if video_bitrate < 200_000:  # 200kbps dan kam bo'lsa — juda kichik
        video_bitrate = 200_000

    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_compressed.mp4"

    try:
        # 2-pass encoding for better quality (but we'll use 1-pass for speed)
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-b:v", str(video_bitrate),
            "-maxrate", str(int(video_bitrate * 1.5)),
            "-bufsize", str(int(video_bitrate * 2)),
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            "-threads", "0",
            output_path,
        ]

        logger.info(f"Video siqish: {video_bitrate // 1000}kbps, duration={duration}s")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"Video siqish xatosi: {stderr.decode()[:300]}")
            return None

        if os.path.exists(output_path):
            new_size = os.path.getsize(output_path)
            logger.info(f"Video siqildi: {new_size / (1024*1024):.1f}MB")
            return output_path

        return None

    except Exception as e:
        logger.error(f"Video compress xatosi: {e}")
        return None


def check_ffmpeg_available() -> bool:
    """ffmpeg o'rnatilganligini tekshirish."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_aria2c_available() -> bool:
    """aria2c o'rnatilganligini tekshirish."""
    try:
        result = subprocess.run(
            ["aria2c", "--version"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
