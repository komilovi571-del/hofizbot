"""
Instagram / social media fallback downloader — cobalt.tools v10 API orqali.

Railway kabi datacenter IP'lari Instagram tomonidan bloklanadi. yt-dlp
muvaffaqiyatsiz bo'lganda, bu modul public cobalt.tools v10 serveriga
so'rov yuborib, media'ni yuklab beradi.

https://github.com/imputnet/cobalt
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

# Cobalt.tools v10 public instance'lari. Yangilari: https://instances.hyper.lol/
_COBALT_INSTANCES = [
    "https://dwnld.nichind.dev/",
    "https://cobalt.api.timelessnesses.me/",
    "https://c-api.zvbi.de/",
]

_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


async def cobalt_download(
    url: str,
    temp_dir: str,
    timeout_sec: int = 60,
) -> Optional[dict]:
    """
    URL'ni cobalt.tools v10 API orqali yuklab olishga urinish.

    Muvaffaqiyatli bo'lsa: {"file_path": str, "title": str, "filesize": int}
    Muvaffaqiyatsiz bo'lsa: None
    """
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    payload = {
        "url": url,
        "videoQuality": "720",
        "audioFormat": "mp3",
        "filenameStyle": "basic",
        "downloadMode": "auto",
    }

    async with aiohttp.ClientSession(timeout=timeout, headers=_HEADERS) as session:
        for api_url in _COBALT_INSTANCES:
            try:
                async with session.post(api_url, json=payload) as resp:
                    if resp.status >= 500:
                        logger.debug(f"Cobalt {api_url} HTTP {resp.status}")
                        continue
                    try:
                        data = await resp.json(content_type=None)
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Cobalt {api_url} xato: {e}")
                continue

            status = (data or {}).get("status", "")
            logger.debug(f"Cobalt {api_url} status={status}")

            if status in ("stream", "redirect", "tunnel"):
                dl_url = data.get("url") or ""
                if not dl_url:
                    continue
                try:
                    return await _download_to_file(session, dl_url, temp_dir)
                except Exception as e:
                    logger.warning(f"Cobalt fayl yuklashda xato: {e}")
                    continue
            elif status == "picker":
                items = data.get("picker") or []
                if items:
                    first = items[0]
                    dl_url = first.get("url", "")
                    if dl_url:
                        try:
                            return await _download_to_file(session, dl_url, temp_dir)
                        except Exception as e:
                            logger.warning(f"Cobalt picker xato: {e}")
                            continue

    logger.warning(f"Hech bir cobalt instance URL'ni yuklay olmadi: {url}")
    return None


async def _download_to_file(
    session: aiohttp.ClientSession,
    url: str,
    temp_dir: str,
) -> dict:
    """Direct URL'dan faylni yuklab olish."""
    os.makedirs(temp_dir, exist_ok=True)
    ext = "mp4"
    lower = url.lower()
    for e in ("mp4", "webm", "mov", "jpg", "jpeg", "png", "mp3", "m4a"):
        if f".{e}" in lower:
            ext = e
            break

    filename = f"ig_fallback_{int(time.time())}.{ext}"
    path = os.path.join(temp_dir, filename)

    async with session.get(url) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            async for chunk in r.content.iter_chunked(64 * 1024):
                f.write(chunk)

    size = os.path.getsize(path) if os.path.exists(path) else 0
    if size == 0:
        try:
            os.remove(path)
        except Exception:
            pass
        raise RuntimeError("Bo'sh fayl")

    logger.info(
        f"Cobalt fallback muvaffaqiyatli: {path} ({size / 1024 / 1024:.1f} MB)"
    )
    return {
        "file_path": path,
        "title": "Instagram media",
        "filesize": size,
    }
