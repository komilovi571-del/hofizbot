"""
Progress Tracker — yt-dlp yuklanish jarayonini Telegram xabariga ko'rsatish.

yt-dlp progress_hooks orqali yuklanish foizini oladi va
Telegram xabarini har 3 soniyada yangilaydi (API rate limit uchun).
"""

import asyncio
import logging
import time
from typing import Any

from aiogram import Bot

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Yuklanish progressini kuzatuvchi va Telegram xabariga yozuvchi.

    Telegram Bot API rate limitini hisobga olgan holda
    xabarni har 3 soniyada yangilaydi.
    """

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        message_id: int,
        update_interval: float = 3.0,
    ):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
        self.update_interval = update_interval
        self._last_update = 0.0
        self._last_text = ""

    def create_hook(self):
        """yt-dlp uchun progress hook funksiyasini yaratish."""
        def hook(d: dict[str, Any]) -> None:
            status = d.get("status", "")
            if status == "downloading":
                percent = d.get("_percent_str", "0%").strip()
                speed = d.get("_speed_str", "N/A").strip()
                eta = d.get("_eta_str", "N/A").strip()
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                # Tez-tez yangilamaslik uchun
                now = time.time()
                if now - self._last_update < self.update_interval:
                    return
                self._last_update = now

                # Progress bar yaratish
                try:
                    pct = float(percent.replace("%", ""))
                except (ValueError, AttributeError):
                    pct = 0

                bar = _progress_bar(pct)

                text = (
                    f"⏳ <b>Yuklanmoqda...</b>\n\n"
                    f"{bar} {percent}\n"
                    f"⚡ Tezlik: {speed}\n"
                    f"⏱ Qoldi: {eta}"
                )

                if text != self._last_text:
                    self._last_text = text
                    # Sinxron hook ichida async funksiyani chaqirish
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(self._update_message(text))
                    except RuntimeError:
                        pass

            elif status == "finished":
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(
                            self._update_message("🔄 <b>Qayta ishlash...</b>\n\nffmpeg bilan format o'zgartirilmoqda...")
                        )
                except RuntimeError:
                    pass

        return hook

    async def _update_message(self, text: str) -> None:
        """Telegram xabarini yangilash."""
        try:
            await self.bot.edit_message_text(
                text=text,
                chat_id=self.chat_id,
                message_id=self.message_id,
                parse_mode="HTML",
            )
        except Exception:
            pass  # Xabar o'chirilgan yoki o'zgartirilgan bo'lishi mumkin


def _progress_bar(percent: float, length: int = 20) -> str:
    """Matnli progress bar yaratish."""
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"


def format_speed(bytes_per_sec: float) -> str:
    """Tezlikni formatlash."""
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f} KB/s"
    elif bytes_per_sec < 1024 * 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    else:
        return f"{bytes_per_sec / (1024 * 1024 * 1024):.2f} GB/s"
