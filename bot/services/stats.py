"""
Stats Service — foydalanuvchilar va yuklanishlar statistikasi.

JSON faylda saqlanadi. Yozish debounce qilingan: mutatsiyalar
tezkor (RAM'da), diskka yozish fon vazifasi orqali davriy amalga oshadi.
"""

import asyncio
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StatsService:
    """JSON-based stats tracking service (debounced writes)."""

    #: Diskka avtomatik yozish intervali (soniya)
    FLUSH_INTERVAL = 5.0

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.data_file = os.path.join(data_dir, "stats.json")
        # RAM mutatsiyalari uchun sync lock (fast path, contention deyarli yo'q)
        self._lock = threading.Lock()
        self._data: dict = {
            "users": {},
            "total_downloads": 0,
            "total_searches": 0,
            "total_shazam": 0,
            "daily_downloads": {},
            "daily_users": {},
        }
        # Dirty flag: mutatsiyadan keyin True, flush'dan keyin False
        self._dirty = False
        self._flush_task: asyncio.Task | None = None
        self._load()
        # daily_users ichidagi list'larni set ga o'girish (tez in-check)
        self._daily_users_sets: dict[str, set[int]] = {
            date: set(users) for date, users in self._data.get("daily_users", {}).items()
        }

    def start_background_flush(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Fon yozish vazifasini ishga tushirish (main loop'dan chaqirilishi kerak)."""
        if self._flush_task and not self._flush_task.done():
            return
        loop = loop or asyncio.get_event_loop()
        self._flush_task = loop.create_task(self._flush_loop())

    async def stop_background_flush(self) -> None:
        """Fon vazifasini to'xtatish va oxirgi marta saqlash."""
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except (asyncio.CancelledError, Exception):
                pass
        await self.flush()

    async def _flush_loop(self) -> None:
        """Dirty bo'lsa har FLUSH_INTERVAL soniyada diskka yozish."""
        try:
            while True:
                await asyncio.sleep(self.FLUSH_INTERVAL)
                if self._dirty:
                    await self.flush()
        except asyncio.CancelledError:
            raise

    async def flush(self) -> None:
        """Stats'ni diskka yozish (run_in_executor orqali event loop'ni bloklamaydi)."""
        if not self._dirty:
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._save_sync)
        except Exception as e:
            logger.warning(f"Stats flush xatosi: {e}")

    def _load(self):
        """JSON fayldan statistikani yuklash."""
        try:
            Path(self.data_dir).mkdir(parents=True, exist_ok=True)
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.info(
                    f"Stats yuklandi: {len(self._data.get('users', {}))} foydalanuvchi"
                )
        except Exception as e:
            logger.warning(f"Stats yuklash xatosi: {e}")

    def _save_sync(self):
        """Statistikani JSON faylga atomik yozish (sync, executor ichida)."""
        try:
            Path(self.data_dir).mkdir(parents=True, exist_ok=True)
            # Dirty bayrog'ini yozishdan oldin tushiramiz — yozish davomida
            # yangi mutatsiyalar kelsa, keyingi flushda ushlanadi.
            with self._lock:
                self._dirty = False
                # daily_users set → list (JSON serializable)
                self._data["daily_users"] = {
                    date: list(users) for date, users in self._daily_users_sets.items()
                }
                payload = json.dumps(self._data, ensure_ascii=False)
            tmp = f"{self.data_file}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self.data_file)
        except Exception as e:
            logger.warning(f"Stats saqlash xatosi: {e}")
            # Keyingi flushda qayta urinish uchun dirty'ni qaytarib qo'yamiz
            with self._lock:
                self._dirty = True

    def _mark_dirty(self):
        """Keyingi flushda diskka yozilishini belgilash."""
        self._dirty = True

    def track_user(
        self, user_id: int, username: str = "", full_name: str = ""
    ):
        """Foydalanuvchini kuzatish."""
        with self._lock:
            uid = str(user_id)
            today = datetime.now().strftime("%Y-%m-%d")

            if uid not in self._data["users"]:
                self._data["users"][uid] = {
                    "username": username,
                    "full_name": full_name,
                    "first_seen": today,
                    "last_seen": today,
                    "downloads": 0,
                    "searches": 0,
                }
            else:
                self._data["users"][uid]["last_seen"] = today
                if username:
                    self._data["users"][uid]["username"] = username
                if full_name:
                    self._data["users"][uid]["full_name"] = full_name

            # Kunlik aktiv foydalanuvchilar (set — O(1) in-check)
            self._daily_users_sets.setdefault(today, set()).add(user_id)

            self._mark_dirty()

    def increment_downloads(self, user_id: int = 0, platform: str = ""):
        """Yuklanishlar sonini oshirish (platform ixtiyoriy: youtube/instagram/...)."""
        with self._lock:
            self._data["total_downloads"] = self._data.get("total_downloads", 0) + 1
            today = datetime.now().strftime("%Y-%m-%d")
            self._data.setdefault("daily_downloads", {})
            self._data["daily_downloads"][today] = (
                self._data["daily_downloads"].get(today, 0) + 1
            )

            # Platform statistikasi
            if platform:
                plat = self._data.setdefault("platforms", {})
                key = platform.lower()
                plat[key] = plat.get(key, 0) + 1

            if user_id:
                uid = str(user_id)
                if uid in self._data["users"]:
                    self._data["users"][uid]["downloads"] = (
                        self._data["users"][uid].get("downloads", 0) + 1
                    )
            self._mark_dirty()

    def increment_searches(self, user_id: int = 0):
        """Qidiruv sonini oshirish."""
        with self._lock:
            self._data["total_searches"] = self._data.get("total_searches", 0) + 1
            if user_id:
                uid = str(user_id)
                if uid in self._data["users"]:
                    self._data["users"][uid]["searches"] = (
                        self._data["users"][uid].get("searches", 0) + 1
                    )
            self._mark_dirty()

    def increment_shazam(self):
        """Shazam so'rovlarini oshirish."""
        with self._lock:
            self._data["total_shazam"] = self._data.get("total_shazam", 0) + 1
            self._mark_dirty()

    def get_all_user_ids(self) -> list[int]:
        """Barcha foydalanuvchi IDlari."""
        return [int(uid) for uid in self._data.get("users", {}).keys()]

    def get_user_count(self) -> int:
        return len(self._data.get("users", {}))

    def get_stats(self) -> dict:
        """Umumiy statistika."""
        today = datetime.now().strftime("%Y-%m-%d")
        daily_downloads = self._data.get("daily_downloads", {})

        return {
            "total_users": len(self._data.get("users", {})),
            "total_downloads": self._data.get("total_downloads", 0),
            "total_searches": self._data.get("total_searches", 0),
            "total_shazam": self._data.get("total_shazam", 0),
            "today_downloads": daily_downloads.get(today, 0),
            "today_active_users": len(self._daily_users_sets.get(today, set())),
            "top_users": self._get_top_users(10),
            "daily_downloads": dict(daily_downloads),
            "daily_active_users": {d: len(u) for d, u in self._daily_users_sets.items()},
            "platforms": dict(self._data.get("platforms", {})),
            "banned_count": sum(
                1 for u in self._data.get("users", {}).values() if u.get("banned")
            ),
            "languages": self._lang_breakdown(),
        }

    def _lang_breakdown(self) -> dict:
        """Foydalanuvchilar til bo'yicha taqsimoti."""
        result: dict[str, int] = {}
        for u in self._data.get("users", {}).values():
            lng = u.get("lang") or "unset"
            result[lng] = result.get(lng, 0) + 1
        return result

    def _get_top_users(self, limit: int = 10) -> list[dict]:
        """Eng ko'p yuklagan foydalanuvchilar."""
        users = self._data.get("users", {})
        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get("downloads", 0),
            reverse=True,
        )[:limit]
        return [
            {
                "user_id": int(uid),
                "username": data.get("username", ""),
                "full_name": data.get("full_name", ""),
                "downloads": data.get("downloads", 0),
            }
            for uid, data in sorted_users
        ]

    def get_user_info(self, user_id: int) -> dict | None:
        """Foydalanuvchi haqida ma'lumot."""
        return self._data.get("users", {}).get(str(user_id))

    def ban_user(self, user_id: int) -> bool:
        """Foydalanuvchini ban qilish."""
        with self._lock:
            uid = str(user_id)
            if uid in self._data.get("users", {}):
                self._data["users"][uid]["banned"] = True
                self._mark_dirty()
                return True
            return False

    def unban_user(self, user_id: int) -> bool:
        """Foydalanuvchini unban qilish."""
        with self._lock:
            uid = str(user_id)
            if uid in self._data.get("users", {}):
                self._data["users"][uid]["banned"] = False
                self._mark_dirty()
                return True
            return False

    def is_banned(self, user_id: int) -> bool:
        """Ban holatini tekshirish."""
        uid = str(user_id)
        user = self._data.get("users", {}).get(uid, {})
        return user.get("banned", False)

    # ===== Til (i18n) =====

    def get_lang(self, user_id: int) -> str | None:
        """Foydalanuvchining saqlangan tilini olish (None — hali tanlamagan)."""
        uid = str(user_id)
        user = self._data.get("users", {}).get(uid)
        if not user:
            return None
        return user.get("lang")

    def set_lang(self, user_id: int, lang: str) -> None:
        """Foydalanuvchi tilini saqlash."""
        with self._lock:
            uid = str(user_id)
            users = self._data.setdefault("users", {})
            if uid not in users:
                today = datetime.now().strftime("%Y-%m-%d")
                users[uid] = {
                    "username": "",
                    "full_name": "",
                    "first_seen": today,
                    "last_seen": today,
                    "downloads": 0,
                    "searches": 0,
                }
            users[uid]["lang"] = lang
            self._mark_dirty()

    def cleanup_old_daily(self, keep_days: int = 30):
        """Eski kunlik statistikani tozalash."""
        with self._lock:
            today = datetime.now()
            for key in ["daily_downloads"]:
                data = self._data.get(key, {})
                to_remove = []
                for date_str in data:
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        if (today - date).days > keep_days:
                            to_remove.append(date_str)
                    except ValueError:
                        to_remove.append(date_str)
                for d in to_remove:
                    del data[d]
            # daily_users_sets uchun ham xuddi shunday
            to_remove = []
            for date_str in self._daily_users_sets:
                try:
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    if (today - date).days > keep_days:
                        to_remove.append(date_str)
                except ValueError:
                    to_remove.append(date_str)
            for d in to_remove:
                self._daily_users_sets.pop(d, None)
            self._mark_dirty()
