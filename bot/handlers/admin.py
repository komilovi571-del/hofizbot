"""Admin Panel — professional bot boshqaruv paneli.

Tugmalar tartibi:
    [📊 Statistika] [👥 Foydalanuvchilar]
    [📢 Xabar yuborish] [📡 Kanal boshqaruvi]
    [⚙️ Sozlamalar]

Funksiyalar:
- Statistika: progress bar, 7 kunlik sparkline, top platformalar, tillar
- Foydalanuvchilar: ro'yxat / qidirish / bitta foydalanuvchiga xabar
- Xabar yuborish: hammaga yoki bitta foydalanuvchiga (media + inline tugma)
- Kanal boshqaruvi: admin_channels router'da (alohida)
- Sozlamalar: bot parametrlari + "Tizim holati" sub-tugmasi
"""

import asyncio
import logging
import os
import platform as pf
import time as _time
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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


# ===== Reply tugma matnlari (admin panel — uz-lotin) =====
BTN_STATS = "📊 Statistika"
BTN_USERS = "👥 Foydalanuvchilar"
BTN_BROADCAST = "📢 Xabar yuborish"
BTN_CHANNELS = "📡 Kanal boshqaruvi"
BTN_SETTINGS = "⚙️ Sozlamalar"

ADMIN_BUTTONS = {BTN_STATS, BTN_USERS, BTN_BROADCAST, BTN_CHANNELS, BTN_SETTINGS}


class BroadcastStates(StatesGroup):
    waiting_message = State()
    waiting_user_id_for_single = State()
    waiting_message_for_single = State()


class SearchStates(StatesGroup):
    waiting_user_id = State()


# ===== Helper'lar =====


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _admin_reply_kb() -> ReplyKeyboardMarkup:
    """Admin panel — Reply klaviatura."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_USERS)],
            [KeyboardButton(text=BTN_BROADCAST), KeyboardButton(text=BTN_CHANNELS)],
            [KeyboardButton(text=BTN_SETTINGS)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Admin amalini tanlang…",
    )


def _format_uptime() -> str:
    uptime = _time.time() - _bot_start_time
    h, rem = divmod(int(uptime), 3600)
    m, s = divmod(rem, 60)
    d, h = divmod(h, 24)
    if d > 0:
        return f"{d} kun {h} soat {m} daqiqa"
    if h > 0:
        return f"{h} soat {m} daqiqa"
    return f"{m} daqiqa {s} soniya"


def _progress_bar(value: int, maximum: int, width: int = 10) -> str:
    """Yigma progress bar: █████░░░░░."""
    if maximum <= 0:
        return "░" * width
    filled = min(width, int(round(value / maximum * width)))
    return "█" * filled + "░" * (width - filled)


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[int]) -> str:
    """Raqamlar ketma-ketligidan Unicode sparkline."""
    if not values:
        return "—"
    mx = max(values)
    if mx <= 0:
        return _SPARK_CHARS[0] * len(values)
    result = []
    for v in values:
        idx = int((v / mx) * (len(_SPARK_CHARS) - 1))
        result.append(_SPARK_CHARS[idx])
    return "".join(result)


def _last7_downloads(stats: dict) -> list[int]:
    """Oxirgi 7 kunlik yuklanishlar ro'yxati (eski → yangi)."""
    daily = stats.get("daily_downloads", {})
    today = datetime.now().date()
    out = []
    for i in range(6, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        out.append(int(daily.get(d, 0)))
    return out


def _platform_emoji(name: str) -> str:
    return {
        "youtube": "📺",
        "instagram": "📸",
        "tiktok": "🎵",
        "facebook": "📘",
        "twitter": "🐦",
        "pinterest": "📌",
        "likee": "💫",
        "snapchat": "👻",
        "reddit": "👽",
        "spotify": "🎧",
        "soundcloud": "🔊",
    }.get(name.lower(), "🔗")


def _lang_emoji(code: str) -> str:
    return {
        "uz": "🇺🇿",
        "uz_cyrl": "🇺🇿",
        "ru": "🇷🇺",
        "en": "🇬🇧",
        "unset": "❔",
    }.get(code, "🌐")


# ===================== /admin =====================


@router.message(Command("admin"))
async def cmd_admin(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return

    stats = stats_service.get_stats()
    text = (
        "🛡 <b>Admin Panel</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>  "
        f"(🚫 {stats.get('banned_count', 0)})\n"
        f"📥 Yuklanishlar: <b>{stats['total_downloads']}</b>\n"
        f"🔍 Qidiruvlar: <b>{stats['total_searches']}</b>\n"
        f"🎵 Shazam: <b>{stats['total_shazam']}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>Bugun:</b>  📥 {stats['today_downloads']}  |  "
        f"👥 {stats['today_active_users']} aktiv\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>\n\n"
        "Quyidagi tugmalardan birini tanlang 👇"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_admin_reply_kb())


# ===================== 📊 Statistika =====================


@router.message(F.text == BTN_STATS)
async def admin_stats_msg(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return

    stats = stats_service.get_stats()
    last7 = _last7_downloads(stats)
    total7 = sum(last7)
    max_day = max(last7) if last7 else 0
    today_dl = stats["today_downloads"]
    today_active = stats["today_active_users"]
    total_users = stats["total_users"]

    # Progress bar: bugungi yuklanishlar — oxirgi 7 kundagi eng yuqori kun nisbatida
    bar_today = _progress_bar(today_dl, max_day or 1, 14)
    bar_active = _progress_bar(today_active, total_users or 1, 14)

    text = (
        "📊 <b>Batafsil Statistika</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<b>📈 Umumiy ko'rsatkichlar</b>\n"
        f"  👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"  📥 Yuklanishlar: <b>{stats['total_downloads']:,}</b>\n"
        f"  🔍 Qidiruvlar: <b>{stats['total_searches']:,}</b>\n"
        f"  🎵 Shazam: <b>{stats['total_shazam']:,}</b>\n"
        f"  🚫 Ban qilinganlar: <b>{stats.get('banned_count', 0)}</b>\n\n"
        "<b>📅 Bugungi kun</b>\n"
        f"  📥 Yuklanish: {bar_today} <b>{today_dl}</b>\n"
        f"  👥 Aktiv: {bar_active} <b>{today_active}</b>\n\n"
        "<b>📉 Oxirgi 7 kun</b>\n"
        f"  <code>{_sparkline(last7)}</code>  "
        f"jami <b>{total7}</b>  |  pik <b>{max_day}</b>\n"
    )

    # Top platformalar
    platforms = stats.get("platforms", {})
    if platforms:
        text += "\n<b>🏆 Platformalar reytingi</b>\n"
        top_plats = sorted(platforms.items(), key=lambda x: x[1], reverse=True)[:6]
        plat_max = top_plats[0][1] if top_plats else 1
        for name, count in top_plats:
            bar = _progress_bar(count, plat_max, 10)
            text += f"  {_platform_emoji(name)} <b>{name}</b> {bar} {count}\n"

    # Tillar
    langs = stats.get("languages", {})
    if langs:
        text += "\n<b>🌐 Tillar</b>\n"
        for code, count in sorted(langs.items(), key=lambda x: x[1], reverse=True):
            text += f"  {_lang_emoji(code)} <code>{code}</code> — <b>{count}</b>\n"

    # Top foydalanuvchilar
    top = stats.get("top_users", [])[:5]
    if top:
        text += "\n<b>🥇 Top foydalanuvchilar</b>\n"
        medals = ["🥇", "🥈", "🥉", "4.", "5."]
        for i, u in enumerate(top):
            name = u.get("full_name") or u.get("username") or str(u["user_id"])
            if len(name) > 20:
                name = name[:20] + "…"
            text += f"  {medals[i]} {name} — <b>{u['downloads']}</b>\n"

    text += f"\n⏱ Uptime: <b>{_format_uptime()}</b>"

    await message.answer(text, parse_mode="HTML")


# ===================== 👥 Foydalanuvchilar =====================


def _users_submenu_kb() -> InlineKeyboardMarkup:
    """Foydalanuvchilar sub-menyu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Qidirish", callback_data="adm:u:search"),
                InlineKeyboardButton(
                    text="✉️ Bitta foydalanuvchiga", callback_data="adm:u:msg1"
                ),
            ],
            [
                InlineKeyboardButton(text="📋 Ro'yxat", callback_data="adm:u:list"),
            ],
        ]
    )


@router.message(F.text == BTN_USERS)
async def admin_users_msg(
    message: Message, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    stats = stats_service.get_stats()
    text = (
        "👥 <b>Foydalanuvchilar bo'limi</b>\n\n"
        f"Jami: <b>{stats['total_users']}</b>\n"
        f"Ban qilinganlar: <b>{stats.get('banned_count', 0)}</b>\n"
        f"Bugun aktiv: <b>{stats['today_active_users']}</b>\n\n"
        "Quyidagi amallardan birini tanlang:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_users_submenu_kb())


@router.callback_query(F.data == "adm:u:list")
async def cb_users_list(
    callback: CallbackQuery, config: Config, stats_service: StatsService
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    user_ids = stats_service.get_all_user_ids()
    total = len(user_ids)
    text = f"📋 <b>Foydalanuvchilar ro'yxati ({total})</b>\n\n"
    for uid in list(reversed(user_ids))[:25]:
        info = stats_service.get_user_info(uid)
        if not info:
            continue
        name = info.get("full_name", "") or ""
        username = info.get("username", "") or ""
        downloads = info.get("downloads", 0)
        banned = "🚫 " if info.get("banned") else ""
        display = f"@{username}" if username else (name[:20] or str(uid))
        text += f"  {banned}<code>{uid}</code> | {display} | {downloads}\n"
    if total > 25:
        text += f"\n... va yana {total - 25} ta"

    back = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm:u:back")]
        ]
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back)
    await callback.answer()


@router.callback_query(F.data == "adm:u:back")
async def cb_users_back(callback: CallbackQuery, config: Config) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    try:
        await callback.message.edit_text(
            "👥 <b>Foydalanuvchilar bo'limi</b>\n\nQuyidagi amallardan birini tanlang:",
            parse_mode="HTML",
            reply_markup=_users_submenu_kb(),
        )
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "adm:u:search")
async def cb_users_search(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(SearchStates.waiting_user_id)
    await callback.message.answer(
        "🔍 <b>Foydalanuvchi qidirish</b>\n\n"
        "ID raqamini yoki @username yuboring.\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
    )
    await callback.answer()


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
    # Admin reply tugmani bossa — state'ni tozalab chiqamiz
    if text_in in ADMIN_BUTTONS:
        await state.clear()
        await message.answer("ℹ️ Qidiruv bekor qilindi. Tugmani qayta bosing.")
        return

    await state.clear()
    info = None
    user_id = None
    if text_in.startswith("@"):
        uname = text_in[1:].lower()
        for uid in stats_service.get_all_user_ids():
            u = stats_service.get_user_info(uid)
            if u and (u.get("username", "").lower() == uname):
                info = u
                user_id = uid
                break
        if not info:
            await message.reply("❌ Username topilmadi.")
            return
    else:
        try:
            user_id = int(text_in)
        except ValueError:
            await message.reply("❌ Noto'g'ri ID. Raqam yoki @username yuboring.")
            return
        info = stats_service.get_user_info(user_id)
        if not info:
            await message.reply("❌ Foydalanuvchi topilmadi.")
            return

    await _show_user_card(message, user_id, info)


async def _show_user_card(message: Message, user_id: int, info: dict) -> None:
    banned_text = "Ha" if info.get("banned") else "Yo'q"
    lang = info.get("lang") or "—"
    reply = (
        f"👤 <b>Foydalanuvchi ma'lumoti</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"👤 Ism: {info.get('full_name', 'N/A')}\n"
        f"🏷 Username: @{info.get('username', 'N/A')}\n"
        f"🌐 Til: <code>{lang}</code>\n"
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
    b.button(text="✉️ Xabar yuborish", callback_data=f"adm:u:msgto:{user_id}")
    b.adjust(2)
    await message.answer(reply, parse_mode="HTML", reply_markup=b.as_markup())


# ===== /user buyrug'i (tez qidirish) =====


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
    await _show_user_card(message, user_id, info)


# ===== Ban / Unban =====


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
    b.button(text="✉️ Xabar yuborish", callback_data=f"adm:u:msgto:{uid}")
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
    b.button(text="✉️ Xabar yuborish", callback_data=f"adm:u:msgto:{uid}")
    b.adjust(2)
    try:
        old_text = callback.message.text or ""
        new_text = old_text.replace("🚫 Ban: Ha", "🚫 Ban: Yo'q")
        await callback.message.edit_text(
            new_text, parse_mode="HTML", reply_markup=b.as_markup()
        )
    except Exception:
        pass


# ===================== 📢 Xabar yuborish =====================


def _broadcast_submenu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Hammaga", callback_data="adm:bc:all"),
                InlineKeyboardButton(
                    text="✉️ Bitta foydalanuvchiga", callback_data="adm:bc:one"
                ),
            ]
        ]
    )


@router.message(F.text == BTN_BROADCAST)
async def admin_broadcast_msg(
    message: Message, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await message.answer(
        "📢 <b>Xabar yuborish</b>\n\n"
        "Tanlang — hammaga yuborasizmi yoki bitta foydalanuvchigami?",
        parse_mode="HTML",
        reply_markup=_broadcast_submenu_kb(),
    )


@router.callback_query(F.data == "adm:bc:all")
async def cb_bc_all(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_message)
    cancel = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="adm:cancel_bc")]
        ]
    )
    try:
        await callback.message.edit_text(
            "📢 <b>Hammaga xabar</b>\n\n"
            "Istalgan xabarni yuboring — matn, rasm, video, audio, "
            "fayl, media-gruppa, forward, poll.\n"
            "Inline URL tugmalar ham qo'llaniladi.\n\n"
            "Xabar 1:1 nusxalanib barcha foydalanuvchilarga yuboriladi.",
            parse_mode="HTML",
            reply_markup=cancel,
        )
    except Exception:
        await callback.message.answer(
            "📢 Xabaringizni yuboring.", reply_markup=cancel
        )
    await callback.answer()


@router.callback_query(F.data == "adm:bc:one")
async def cb_bc_one(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_user_id_for_single)
    await callback.message.answer(
        "✉️ <b>Bitta foydalanuvchiga xabar</b>\n\n"
        "Foydalanuvchi ID yoki @username yuboring.\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:u:msgto:"))
async def cb_msg_to_user(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    """User kartasidagi 'Xabar yuborish' tugmasi — birdan single-user FSM'ga o'tamiz."""
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    uid = int(callback.data.split(":")[3])
    await state.set_state(BroadcastStates.waiting_message_for_single)
    await state.update_data(target_user_id=uid)
    await callback.message.answer(
        f"✉️ Foydalanuvchi <code>{uid}</code> uchun xabarni yuboring.\n"
        "Matn, media, forward — hammasi qo'llaniladi.\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "adm:u:msg1")
async def cb_u_msg1(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    """Foydalanuvchilar sub-menyudan 'Bitta foydalanuvchiga' — ID so'raladi."""
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_user_id_for_single)
    await callback.message.answer(
        "✉️ Foydalanuvchi ID yoki @username yuboring.\n/cancel — bekor qilish."
    )
    await callback.answer()


@router.message(BroadcastStates.waiting_user_id_for_single, Command("cancel"))
async def _bc_single_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(BroadcastStates.waiting_user_id_for_single, F.text)
async def _bc_single_id(
    message: Message,
    config: Config,
    stats_service: StatsService,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    text_in = (message.text or "").strip()
    if text_in in ADMIN_BUTTONS:
        await state.clear()
        await message.answer("ℹ️ Bekor qilindi. Tugmani qayta bosing.")
        return

    target_id = None
    if text_in.startswith("@"):
        uname = text_in[1:].lower()
        for uid in stats_service.get_all_user_ids():
            u = stats_service.get_user_info(uid)
            if u and u.get("username", "").lower() == uname:
                target_id = uid
                break
        if not target_id:
            await message.reply("❌ Username topilmadi. Qayta yuboring yoki /cancel.")
            return
    else:
        try:
            target_id = int(text_in)
        except ValueError:
            await message.reply("❌ Noto'g'ri ID. Qayta yuboring yoki /cancel.")
            return

    await state.update_data(target_user_id=target_id)
    await state.set_state(BroadcastStates.waiting_message_for_single)
    await message.answer(
        f"✅ Manzil: <code>{target_id}</code>\n\n"
        "Endi yubormoqchi bo'lgan xabaringizni yuboring (matn, media, forward).\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
    )


@router.message(BroadcastStates.waiting_message_for_single, Command("cancel"))
async def _bc_single_msg_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(BroadcastStates.waiting_message_for_single)
async def _bc_single_send(
    message: Message,
    bot: Bot,
    config: Config,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    # Admin reply tugmani bossa — bekor qilish
    if (message.text or "").strip() in ADMIN_BUTTONS:
        await state.clear()
        await message.answer("ℹ️ Bekor qilindi. Tugmani qayta bosing.")
        return

    data = await state.get_data()
    target_id = data.get("target_user_id")
    await state.clear()
    if not target_id:
        await message.reply("❌ Manzil topilmadi. Qaytadan boshlang.")
        return
    try:
        await message.copy_to(
            chat_id=target_id,
            reply_markup=message.reply_markup,  # Inline tugmalar bo'lsa ham yuboriladi
        )
        await message.reply(f"✅ <code>{target_id}</code> ga yuborildi.", parse_mode="HTML")
    except Exception as e:
        await message.reply(f"❌ Yuborib bo'lmadi: <code>{e}</code>", parse_mode="HTML")


# ===== Hammaga broadcast =====


@router.callback_query(F.data == "adm:cancel_bc")
async def admin_cancel_broadcast(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        return
    await state.clear()
    try:
        await callback.message.edit_text("❌ Bekor qilindi.", parse_mode="HTML")
    except Exception:
        pass
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
    if (message.text or "").strip() in ADMIN_BUTTONS:
        await state.clear()
        await message.answer("ℹ️ Bekor qilindi. Tugmani qayta bosing.")
        return

    await state.clear()
    user_ids = stats_service.get_all_user_ids()
    total = len(user_ids)
    if total == 0:
        await message.reply("❌ Foydalanuvchilar topilmadi.")
        return

    status_msg = await message.reply(
        f"📢 <b>Xabar yuborilmoqda...</b>\n👥 {total} ta foydalanuvchiga...",
        parse_mode="HTML",
    )

    sem = asyncio.Semaphore(25)
    counters = {"sent": 0, "failed": 0, "done": 0}
    status_lock = asyncio.Lock()

    async def _send_one(uid: int) -> None:
        async with sem:
            try:
                await message.copy_to(chat_id=uid, reply_markup=message.reply_markup)
                counters["sent"] += 1
            except Exception:
                counters["failed"] += 1
            finally:
                counters["done"] += 1
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

    await status_msg.edit_text(
        f"📢 <b>Xabar yuborildi!</b>\n\n"
        f"✅ Muvaffaqiyatli: <b>{counters['sent']}</b>\n"
        f"❌ Xato: <b>{counters['failed']}</b>\n"
        f"📊 Jami: <b>{total}</b>",
        parse_mode="HTML",
    )


# ===================== ⚙️ Sozlamalar =====================


def _settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Tizim holati", callback_data="adm:sys"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Yangilash", callback_data="adm:settings_refresh"
                )
            ],
        ]
    )


def _settings_text(config: Config) -> str:
    return (
        "⚙️ <b>Bot Sozlamalari</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Rejim: <b>{config.bot.mode}</b>\n"
        f"📁 Temp: <code>{config.download.temp_dir}</code>\n"
        f"🔄 Max parallel: <b>{config.download.max_concurrent}</b>\n"
        f"👤 Max per user: <b>{config.download.max_per_user}</b>\n"
        f"⏱ Rate limit: <b>{config.download.rate_limit_per_minute}/min</b>\n"
        f"📦 Max fayl: <b>{config.download.max_file_size / (1024**3):.1f} GB</b>\n"
        f"🛡 Adminlar: <code>{config.admin_ids}</code>"
    )


@router.message(F.text == BTN_SETTINGS)
async def admin_settings_msg(message: Message, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await message.answer(
        _settings_text(config), parse_mode="HTML", reply_markup=_settings_kb()
    )


@router.callback_query(F.data == "adm:settings_refresh")
async def cb_settings_refresh(
    callback: CallbackQuery, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            _settings_text(config),
            parse_mode="HTML",
            reply_markup=_settings_kb(),
        )
    except Exception:
        pass
    await callback.answer("🔄")


@router.callback_query(F.data == "adm:sys")
async def cb_system(
    callback: CallbackQuery, config: Config
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return

    text = (
        "📋 <b>Tizim Holati</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 OS: <b>{pf.system()} {pf.release()}</b>\n"
        f"🐍 Python: <b>{pf.python_version()}</b>\n"
        f"⏱ Uptime: <b>{_format_uptime()}</b>\n"
    )
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        mem = proc.memory_info()
        text += f"💾 RAM: <b>{mem.rss / (1024 * 1024):.1f} MB</b>\n"
        text += f"🖥 CPU: <b>{proc.cpu_percent(interval=0.1):.1f}%</b>\n"
        # Jami RAM
        vm = psutil.virtual_memory()
        ram_bar = _progress_bar(int(vm.percent), 100, 14)
        text += f"🧠 Tizim RAM: {ram_bar} <b>{vm.percent:.0f}%</b>\n"
    except ImportError:
        pass
    try:
        temp_dir = config.download.temp_dir
        if os.path.exists(temp_dir):
            total = sum(
                f.stat().st_size for f in Path(temp_dir).rglob("*") if f.is_file()
            )
            text += f"📂 Temp: <b>{total / (1024 * 1024):.1f} MB</b>\n"
    except Exception:
        pass
    from bot.utils.helpers import check_dependencies
    deps = check_dependencies()
    text += "\n<b>Dependencies:</b>\n"
    for dep, ok in deps.items():
        text += f"  {'✅' if ok else '❌'} {dep}\n"

    back = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Sozlamalar", callback_data="adm:settings_refresh")]
        ]
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back)
    await callback.answer()
