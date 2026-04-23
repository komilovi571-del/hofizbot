"""
Admin Panel — Professional bot boshqaruv paneli.

Funksiyalar:
- 📊 Statistika (foydalanuvchilar, yuklanishlar, qidiruvlar)
- 👥 Foydalanuvchilar ro'yxati
- 📢 Xabar yuborish (broadcast)
- 🔍 Foydalanuvchi qidirish / ban / unban
- ⚙️ Bot sozlamalari
- 📋 Tizim ma'lumotlari
"""

import asyncio
import logging
import time as _time
from datetime import datetime
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import Config
from bot.services.stats import StatsService

logger = logging.getLogger(__name__)

router = Router(name="admin")

_bot_start_time = _time.time()


# ===== Reply keyboard tugma matnlari =====
BTN_STATS = "📊 Statistika"
BTN_USERS = "👥 Foydalanuvchilar"
BTN_BROADCAST = "📢 Xabar yuborish"
BTN_SEARCH = "🔍 Foydalanuvchi qidirish"
BTN_SETTINGS = "⚙️ Sozlamalar"
BTN_SYSTEM = "📋 Tizim holati"
BTN_CLOSE = "❌ Yopish"


class BroadcastStates(StatesGroup):
    waiting_message = State()


class SearchStates(StatesGroup):
    waiting_user_id = State()


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _admin_reply_kb() -> ReplyKeyboardMarkup:
    """Admin panel uchun Reply klaviatura."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_USERS)],
            [KeyboardButton(text=BTN_BROADCAST), KeyboardButton(text=BTN_SEARCH)],
            [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_SYSTEM)],
            [KeyboardButton(text=BTN_CLOSE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin amalini tanlang…",
    )


def _admin_menu_kb():
    # Eski inline menyu o'rniga — faqat ba'zi sub-menyu kontekstlari uchun qoldirilgan
    b = InlineKeyboardBuilder()
    b.button(text="📊 Statistika", callback_data="adm:stats")
    b.button(text="👥 Foydalanuvchilar", callback_data="adm:users")
    b.button(text="📢 Xabar yuborish", callback_data="adm:broadcast")
    b.button(text="🔍 Foydalanuvchi qidirish", callback_data="adm:search")
    b.button(text="⚙️ Sozlamalar", callback_data="adm:settings")
    b.button(text="📋 Tizim holati", callback_data="adm:system")
    b.adjust(2)
    return b.as_markup()


def _back_kb():
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Orqaga", callback_data="adm:menu")
    return b.as_markup()


def _format_uptime() -> str:
    uptime = _time.time() - _bot_start_time
    h, rem = divmod(int(uptime), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h} soat {m} daqiqa"
    return f"{m} daqiqa {s} soniya"


# ===================== /admin =====================


@router.message(Command("admin"))
async def cmd_admin(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return

    stats = stats_service.get_stats()
    text = (
        "🛡 <b>Admin Panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"📥 Jami yuklanishlar: <b>{stats['total_downloads']}</b>\n"
        f"🔍 Jami qidiruvlar: <b>{stats['total_searches']}</b>\n"
        f"🎵 Shazam: <b>{stats['total_shazam']}</b>\n\n"
        f"📅 <b>Bugun:</b>\n"
        f"  📥 Yuklanishlar: <b>{stats['today_downloads']}</b>\n"
        f"  👥 Aktiv: <b>{stats['today_active_users']}</b>\n\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>\n\n"
        "Pastdagi tugmalardan birini tanlang 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_admin_reply_kb())


@router.message(F.text == BTN_CLOSE)
async def admin_close_kb(
    message: Message, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await message.answer(
        "✅ Admin panel yopildi.", reply_markup=ReplyKeyboardRemove()
    )


@router.message(F.text == BTN_STATS)
async def admin_stats_msg(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    stats = stats_service.get_stats()
    top = stats.get("top_users", [])
    text = (
        "📊 <b>Batafsil Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"📥 Jami yuklanishlar: <b>{stats['total_downloads']}</b>\n"
        f"🔍 Jami qidiruvlar: <b>{stats['total_searches']}</b>\n"
        f"🎵 Shazam so'rovlar: <b>{stats['total_shazam']}</b>\n\n"
        f"📅 <b>Bugungi statistika:</b>\n"
        f"  📥 Yuklanishlar: <b>{stats['today_downloads']}</b>\n"
        f"  👥 Aktiv: <b>{stats['today_active_users']}</b>\n"
    )
    if top:
        text += "\n🏆 <b>Top foydalanuvchilar:</b>\n"
        for i, u in enumerate(top, 1):
            name = u.get("full_name") or u.get("username") or str(u["user_id"])
            text += f"  {i}. {name} — <b>{u['downloads']}</b> ta\n"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == BTN_USERS)
async def admin_users_msg(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    user_ids = stats_service.get_all_user_ids()
    total = len(user_ids)
    text = f"👥 <b>Foydalanuvchilar ({total} ta)</b>\n\n"
    for uid in list(reversed(user_ids))[:20]:
        info = stats_service.get_user_info(uid)
        if info:
            name = info.get("full_name", "")
            username = info.get("username", "")
            downloads = info.get("downloads", 0)
            banned = "🚫 " if info.get("banned") else ""
            display = f"@{username}" if username else (name or str(uid))
            text += f"  {banned}<code>{uid}</code> | {display} | {downloads} ta\n"
    if total > 20:
        text += f"\n... va yana {total - 20} ta foydalanuvchi"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == BTN_BROADCAST)
async def admin_broadcast_msg(
    message: Message, config: Config, state: FSMContext
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await state.set_state(BroadcastStates.waiting_message)
    b = InlineKeyboardBuilder()
    b.button(text="❌ Bekor qilish", callback_data="adm:cancel_bc")
    await message.answer(
        "📢 <b>Xabar yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n"
        "Matn, rasm, video yoki boshqa xabar yuborishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=b.as_markup(),
    )


@router.message(F.text == BTN_SEARCH)
async def admin_search_msg(
    message: Message, config: Config, state: FSMContext
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await state.set_state(SearchStates.waiting_user_id)
    await message.answer(
        "🔍 <b>Foydalanuvchi qidirish</b>\n\n"
        "Foydalanuvchi ID raqamini yuboring yoki /cancel — bekor qilish.",
        parse_mode="HTML",
    )


@router.message(SearchStates.waiting_user_id, Command("cancel"))
async def admin_search_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(SearchStates.waiting_user_id, F.text)
async def admin_search_receive(
    message: Message,
    config: Config,
    stats_service: StatsService,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    text_in = (message.text or "").strip()
    # Admin tugmani bossa — state'ni tozalab, tugma ishlashiga ruxsat ber
    if text_in in (BTN_STATS, BTN_USERS, BTN_BROADCAST, BTN_SEARCH,
                   BTN_SETTINGS, BTN_SYSTEM, BTN_CLOSE):
        await state.clear()
        # Qayta trigger qilish uchun qayta yo'naltirilmaydi — admin tugmani qayta bossin
        await message.answer("ℹ️ Qidiruv bekor qilindi. Tugmani qayta bosing.")
        return
    try:
        user_id = int(text_in)
    except ValueError:
        await message.reply("❌ Noto'g'ri ID. Raqam yuboring yoki /cancel.")
        return
    await state.clear()
    info = stats_service.get_user_info(user_id)
    if not info:
        await message.reply("❌ Foydalanuvchi topilmadi.")
        return
    banned_text = "Ha" if info.get("banned") else "Yo'q"
    reply = (
        f"👤 <b>Foydalanuvchi</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Ism: {info.get('full_name', 'N/A')}\n"
        f"🏷 Username: @{info.get('username', 'N/A')}\n"
        f"📅 Birinchi: {info.get('first_seen', 'N/A')}\n"
        f"📅 Oxirgi: {info.get('last_seen', 'N/A')}\n"
        f"📥 Yuklanishlar: {info.get('downloads', 0)}\n"
        f"🔍 Qidiruvlar: {info.get('searches', 0)}\n"
        f"🚫 Ban: {banned_text}"
    )
    b = InlineKeyboardBuilder()
    if info.get("banned"):
        b.button(text="✅ Unban", callback_data=f"adm:unban:{user_id}")
    else:
        b.button(text="🚫 Ban", callback_data=f"adm:ban:{user_id}")
    b.adjust(1)
    await message.answer(reply, parse_mode="HTML", reply_markup=b.as_markup())


@router.message(F.text == BTN_SETTINGS)
async def admin_settings_msg(
    message: Message, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    text = (
        "⚙️ <b>Bot Sozlamalari</b>\n\n"
        f"🤖 Rejim: <b>{config.bot.mode}</b>\n"
        f"📁 Temp: <code>{config.download.temp_dir}</code>\n"
        f"🔄 Max parallel: <b>{config.download.max_concurrent}</b>\n"
        f"👤 Max per user: <b>{config.download.max_per_user}</b>\n"
        f"⏱ Rate limit: <b>{config.download.rate_limit_per_minute}/min</b>\n"
        f"📦 Max fayl: <b>{config.download.max_file_size / (1024**2):.0f} MB</b>\n"
        f"🛡 Admin: <code>{config.admin_ids}</code>"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == BTN_SYSTEM)
async def admin_system_msg(
    message: Message, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    import os
    import platform as pf

    text = (
        "📋 <b>Tizim Holati</b>\n\n"
        f"🖥 OS: <b>{pf.system()} {pf.release()}</b>\n"
        f"🐍 Python: <b>{pf.python_version()}</b>\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>\n"
    )
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        text += f"💾 RAM: <b>{mem.rss / (1024*1024):.1f} MB</b>\n"
        text += f"🖥 CPU: <b>{proc.cpu_percent(interval=0.1):.1f}%</b>\n"
    except ImportError:
        pass
    try:
        temp_dir = config.download.temp_dir
        if os.path.exists(temp_dir):
            total = sum(
                f.stat().st_size
                for f in Path(temp_dir).rglob("*")
                if f.is_file()
            )
            text += f"📂 Temp: <b>{total / (1024*1024):.1f} MB</b>\n"
    except Exception:
        pass
    from bot.utils.helpers import check_dependencies
    deps = check_dependencies()
    text += "\n<b>Dependencies:</b>\n"
    for dep, ok in deps.items():
        text += f"  {'✅' if ok else '❌'} {dep}\n"
    await message.answer(text, parse_mode="HTML")


# ===================== /admin (eski callback handler eski xabarlar uchun) =====================


@router.message(Command("admin_old"))
async def cmd_admin_old(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    """Eski inline menyu — legacy /admin_old."""
    if not _is_admin(message.from_user.id, config):
        return
    stats = stats_service.get_stats()
    text = (
        "🛡 <b>Admin Panel (legacy)</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"📥 Jami yuklanishlar: <b>{stats['total_downloads']}</b>\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_admin_menu_kb())


@router.message(Command("myid"))
async def cmd_myid(message: Message) -> None:
    """Foydalanuvchi ID sini ko'rsatish."""
    await message.reply(
        f"🆔 Sizning Telegram ID: <code>{message.from_user.id}</code>",
        parse_mode="HTML",
    )


# ===================== Menuga qaytish =====================


@router.callback_query(F.data == "adm:menu")
async def admin_menu(
    callback: CallbackQuery, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    stats = stats_service.get_stats()
    text = (
        "🛡 <b>Admin Panel</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"📥 Jami yuklanishlar: <b>{stats['total_downloads']}</b>\n"
        f"🔍 Jami qidiruvlar: <b>{stats['total_searches']}</b>\n"
        f"🎵 Shazam: <b>{stats['total_shazam']}</b>\n\n"
        f"📅 <b>Bugun:</b>\n"
        f"  📥 Yuklanishlar: <b>{stats['today_downloads']}</b>\n"
        f"  👥 Aktiv: <b>{stats['today_active_users']}</b>\n\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=_admin_menu_kb()
    )
    await callback.answer()


# ===================== Statistika =====================


@router.callback_query(F.data == "adm:stats")
async def admin_stats(
    callback: CallbackQuery, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    stats = stats_service.get_stats()
    top = stats.get("top_users", [])

    text = (
        "📊 <b>Batafsil Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"📥 Jami yuklanishlar: <b>{stats['total_downloads']}</b>\n"
        f"🔍 Jami qidiruvlar: <b>{stats['total_searches']}</b>\n"
        f"🎵 Shazam so'rovlar: <b>{stats['total_shazam']}</b>\n\n"
        f"📅 <b>Bugungi statistika:</b>\n"
        f"  📥 Yuklanishlar: <b>{stats['today_downloads']}</b>\n"
        f"  👥 Aktiv: <b>{stats['today_active_users']}</b>\n"
    )

    if top:
        text += "\n🏆 <b>Top foydalanuvchilar:</b>\n"
        for i, u in enumerate(top, 1):
            name = u.get("full_name") or u.get("username") or str(u["user_id"])
            text += f"  {i}. {name} — <b>{u['downloads']}</b> ta\n"

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=_back_kb()
    )
    await callback.answer()


# ===================== Foydalanuvchilar =====================


@router.callback_query(F.data == "adm:users")
async def admin_users(
    callback: CallbackQuery, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    user_ids = stats_service.get_all_user_ids()
    total = len(user_ids)

    text = f"👥 <b>Foydalanuvchilar ({total} ta)</b>\n\n"

    for uid in list(reversed(user_ids))[:20]:
        info = stats_service.get_user_info(uid)
        if info:
            name = info.get("full_name", "")
            username = info.get("username", "")
            downloads = info.get("downloads", 0)
            banned = "🚫 " if info.get("banned") else ""
            display = f"@{username}" if username else (name or str(uid))
            text += f"  {banned}<code>{uid}</code> | {display} | {downloads} ta\n"

    if total > 20:
        text += f"\n... va yana {total - 20} ta foydalanuvchi"

    b = InlineKeyboardBuilder()
    b.button(text="📢 Hammaga xabar", callback_data="adm:broadcast")
    b.button(text="⬅️ Orqaga", callback_data="adm:menu")
    b.adjust(1)

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=b.as_markup()
    )
    await callback.answer()


# ===================== Broadcast =====================


@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    await state.set_state(BroadcastStates.waiting_message)

    b = InlineKeyboardBuilder()
    b.button(text="❌ Bekor qilish", callback_data="adm:cancel_bc")

    await callback.message.edit_text(
        "📢 <b>Xabar yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing.\n"
        "Matn, rasm, video yoki boshqa xabar yuborishingiz mumkin.",
        parse_mode="HTML",
        reply_markup=b.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "adm:cancel_bc")
async def admin_cancel_broadcast(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.", parse_mode="HTML")
    await callback.answer()


@router.message(BroadcastStates.waiting_message)
async def admin_broadcast_send(
    message: Message,
    bot: Bot,
    config: Config,
    stats_service: StatsService,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return

    await state.clear()

    user_ids = stats_service.get_all_user_ids()
    total = len(user_ids)

    if total == 0:
        await message.reply("❌ Foydalanuvchilar topilmadi.")
        return

    status_msg = await message.reply(
        f"📢 <b>Xabar yuborilmoqda...</b>\n"
        f"👥 {total} ta foydalanuvchiga...",
        parse_mode="HTML",
    )

    # Parallel yuborish: Telegram 30 msg/s limitidan ham pastroq (25 concurrent)
    sem = asyncio.Semaphore(25)
    counters = {"sent": 0, "failed": 0, "done": 0}
    status_lock = asyncio.Lock()

    async def _send_one(uid: int) -> None:
        async with sem:
            try:
                await message.copy_to(chat_id=uid)
                counters["sent"] += 1
            except Exception:
                counters["failed"] += 1
            finally:
                counters["done"] += 1

            # Har 50 ta yuborilgandan keyin statusni yangilash
            if counters["done"] % 50 == 0:
                async with status_lock:
                    try:
                        await status_msg.edit_text(
                            f"📢 <b>Yuborilmoqda...</b>\n"
                            f"✅ {counters['sent']} | ❌ {counters['failed']} | "
                            f"📊 {counters['done']}/{total}",
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass

    await asyncio.gather(*[_send_one(uid) for uid in user_ids], return_exceptions=True)

    sent = counters["sent"]
    failed = counters["failed"]

    await status_msg.edit_text(
        f"📢 <b>Xabar yuborildi!</b>\n\n"
        f"✅ Muvaffaqiyatli: <b>{sent}</b>\n"
        f"❌ Xato: <b>{failed}</b>\n"
        f"📊 Jami: <b>{total}</b>",
        parse_mode="HTML",
    )


# ===================== Foydalanuvchi qidirish =====================


@router.callback_query(F.data == "adm:search")
async def admin_search_prompt(
    callback: CallbackQuery, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    await callback.message.edit_text(
        "🔍 <b>Foydalanuvchi qidirish</b>\n\n"
        "Foydalanuvchi ID sini yuboring:\n"
        "<code>/user 123456789</code>",
        parse_mode="HTML",
        reply_markup=_back_kb(),
    )
    await callback.answer()


@router.message(Command("user"))
async def cmd_user_info(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "❌ Format: <code>/user 123456789</code>", parse_mode="HTML"
        )
        return

    try:
        user_id = int(args[1].strip())
    except ValueError:
        await message.reply("❌ Noto'g'ri ID.", parse_mode="HTML")
        return

    info = stats_service.get_user_info(user_id)
    if not info:
        await message.reply("❌ Foydalanuvchi topilmadi.")
        return

    banned_text = "Ha" if info.get("banned") else "Yo'q"
    text = (
        f"👤 <b>Foydalanuvchi</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Ism: {info.get('full_name', 'N/A')}\n"
        f"🏷 Username: @{info.get('username', 'N/A')}\n"
        f"📅 Birinchi: {info.get('first_seen', 'N/A')}\n"
        f"📅 Oxirgi: {info.get('last_seen', 'N/A')}\n"
        f"📥 Yuklanishlar: {info.get('downloads', 0)}\n"
        f"🔍 Qidiruvlar: {info.get('searches', 0)}\n"
        f"🚫 Ban: {banned_text}"
    )

    b = InlineKeyboardBuilder()
    if info.get("banned"):
        b.button(text="✅ Unban", callback_data=f"adm:unban:{user_id}")
    else:
        b.button(text="🚫 Ban", callback_data=f"adm:ban:{user_id}")
    b.button(text="⬅️ Orqaga", callback_data="adm:menu")
    b.adjust(2)

    await message.answer(text, parse_mode="HTML", reply_markup=b.as_markup())


# ===================== Ban / Unban =====================


@router.callback_query(F.data.startswith("adm:ban:"))
async def admin_ban(
    callback: CallbackQuery, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    uid = int(callback.data.split(":")[2])
    stats_service.ban_user(uid)
    await callback.answer(f"🚫 {uid} ban qilindi!", show_alert=True)

    b = InlineKeyboardBuilder()
    b.button(text="✅ Unban", callback_data=f"adm:unban:{uid}")
    b.button(text="⬅️ Orqaga", callback_data="adm:menu")
    b.adjust(2)

    try:
        old_text = callback.message.text or ""
        new_text = old_text.replace("🚫 Ban: Yo'q", "🚫 Ban: Ha")
        await callback.message.edit_text(
            new_text, parse_mode="HTML", reply_markup=b.as_markup()
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:unban:"))
async def admin_unban(
    callback: CallbackQuery, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    uid = int(callback.data.split(":")[2])
    stats_service.unban_user(uid)
    await callback.answer(f"✅ {uid} unban qilindi!", show_alert=True)

    b = InlineKeyboardBuilder()
    b.button(text="🚫 Ban", callback_data=f"adm:ban:{uid}")
    b.button(text="⬅️ Orqaga", callback_data="adm:menu")
    b.adjust(2)

    try:
        old_text = callback.message.text or ""
        new_text = old_text.replace("🚫 Ban: Ha", "🚫 Ban: Yo'q")
        await callback.message.edit_text(
            new_text, parse_mode="HTML", reply_markup=b.as_markup()
        )
    except Exception:
        pass


# ===================== Sozlamalar =====================


@router.callback_query(F.data == "adm:settings")
async def admin_settings(
    callback: CallbackQuery, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    text = (
        "⚙️ <b>Bot Sozlamalari</b>\n\n"
        f"🤖 Rejim: <b>{config.bot.mode}</b>\n"
        f"📁 Temp: <code>{config.download.temp_dir}</code>\n"
        f"🔄 Max parallel: <b>{config.download.max_concurrent}</b>\n"
        f"👤 Max per user: <b>{config.download.max_per_user}</b>\n"
        f"⏱ Rate limit: <b>{config.download.rate_limit_per_minute}/min</b>\n"
        f" Max fayl: <b>{config.download.max_file_size / (1024**3):.1f} GB</b>\n"
        f"🛡 Admin: <code>{config.admin_ids}</code>"
    )
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=_back_kb()
    )
    await callback.answer()


# ===================== Tizim holati =====================


@router.callback_query(F.data == "adm:system")
async def admin_system(
    callback: CallbackQuery, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    import os
    import platform as pf

    text = (
        "📋 <b>Tizim Holati</b>\n\n"
        f"🖥 OS: <b>{pf.system()} {pf.release()}</b>\n"
        f"🐍 Python: <b>{pf.python_version()}</b>\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>\n"
    )

    # RAM info
    try:
        import psutil

        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        text += f"💾 RAM: <b>{mem.rss / (1024*1024):.1f} MB</b>\n"
        text += f"🖥 CPU: <b>{proc.cpu_percent(interval=0.1):.1f}%</b>\n"
    except ImportError:
        pass

    # Temp dir size
    try:
        temp_dir = config.download.temp_dir
        if os.path.exists(temp_dir):
            total = sum(
                f.stat().st_size
                for f in Path(temp_dir).rglob("*")
                if f.is_file()
            )
            text += f"📂 Temp: <b>{total / (1024*1024):.1f} MB</b>\n"
    except Exception:
        pass

    # Dependencies
    from bot.utils.helpers import check_dependencies

    deps = check_dependencies()
    text += "\n<b>Dependencies:</b>\n"
    for dep, ok in deps.items():
        text += f"  {'✅' if ok else '❌'} {dep}\n"

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=_back_kb()
    )
    await callback.answer()
