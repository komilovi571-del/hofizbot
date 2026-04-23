"""Admin Channels — kanal boshqaruv handler'lari.

Funksiyalar:
- Kanal qo'shish (forward yoki @username bilan, bot admin ekanligi tekshiriladi)
- Kanallar ro'yxati
- Har bir kanal uchun amallar:
    - 📨 Post yuborish (matn/rasm/video/audio/hujjat/media-guruh/poll/forward)
    - Inline URL tugmalar qo'shish
    - 📌 Pin qilish
    - 📊 Statistika (member count + oxirgi post link)
    - 🗑 Ro'yxatdan o'chirish
"""

import json
import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.config import Config
from bot.handlers.admin import ADMIN_BUTTONS, BTN_CHANNELS
from bot.services.channels import ChannelsService

logger = logging.getLogger(__name__)

router = Router(name="admin_channels")


class ChannelStates(StatesGroup):
    waiting_channel = State()  # forward yoki @username
    waiting_post = State()  # kanalga yuboriladigan post
    waiting_buttons = State()  # inline tugmalar (ixtiyoriy)


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


# ===== Asosiy menyu =====


def _channels_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="ch:add"),
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="ch:list"),
            ]
        ]
    )


@router.message(F.text == BTN_CHANNELS)
async def channels_entry(
    message: Message,
    config: Config,
    channels_service: ChannelsService,
    bot: Bot,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    await _show_channels_list(message, config, channels_service, bot)


async def _show_channels_list(
    target: Message | CallbackQuery,
    config: Config,
    channels_service: ChannelsService,
    bot: Bot,
) -> None:
    admin_id = target.from_user.id
    items = await channels_service.list_channels(admin_id)

    if not items:
        text = (
            "📡 <b>Kanal boshqaruvi</b>\n\n"
            "Hozircha kanal qo'shilmagan.\n\n"
            "➕ <b>Kanal qo'shish</b> tugmasini bosing va botni "
            "kanaliga admin qiling (post yuborish huquqi bilan)."
        )
        kb = _channels_main_kb()
    else:
        text = f"📡 <b>Kanal boshqaruvi</b>\n\nJami: <b>{len(items)}</b> ta\n\n"
        rows: list[list[InlineKeyboardButton]] = []
        for ch in items:
            title = ch.get("title") or (
                f"@{ch['username']}" if ch.get("username") else str(ch["chat_id"])
            )
            if len(title) > 32:
                title = title[:32] + "…"
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"📡 {title}",
                        callback_data=f"ch:open:{ch['chat_id']}",
                    )
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(text="➕ Qo'shish", callback_data="ch:add"),
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="ch:list"),
            ]
        )
        kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        try:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await target.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "ch:list")
async def cb_channels_list(
    callback: CallbackQuery,
    config: Config,
    channels_service: ChannelsService,
    bot: Bot,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    await _show_channels_list(callback, config, channels_service, bot)
    await callback.answer()


# ===== Kanal qo'shish =====


@router.callback_query(F.data == "ch:add")
async def cb_channel_add(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(ChannelStates.waiting_channel)
    await callback.message.answer(
        "➕ <b>Kanal qo'shish</b>\n\n"
        "Quyidagilardan birini yuboring:\n"
        "1️⃣ Kanaldan xabarni forward qiling\n"
        "2️⃣ Kanal @username-ini yuboring\n"
        "3️⃣ Chat ID (masalan: -1001234567890) yuboring\n\n"
        "⚠️ Bot shu kanalda admin bo'lishi va post yuborish huquqi bo'lishi shart.\n\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ChannelStates.waiting_channel, Command("cancel"))
async def add_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(ChannelStates.waiting_channel)
async def add_channel_receive(
    message: Message,
    bot: Bot,
    config: Config,
    channels_service: ChannelsService,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    if (message.text or "").strip() in ADMIN_BUTTONS:
        await state.clear()
        await message.answer("ℹ️ Bekor qilindi. Tugmani qayta bosing.")
        return

    chat_id: int | None = None
    # 1. Forward
    if message.forward_from_chat:
        chat_id = message.forward_from_chat.id
    # 2. Username yoki ID
    elif message.text:
        txt = message.text.strip()
        if txt.startswith("@"):
            try:
                ch = await bot.get_chat(txt)
                chat_id = ch.id
            except Exception as e:
                await message.reply(f"❌ Kanal topilmadi: <code>{e}</code>", parse_mode="HTML")
                return
        else:
            try:
                chat_id = int(txt)
            except ValueError:
                await message.reply("❌ Noto'g'ri format. @username, ID yoki forward yuboring.")
                return

    if chat_id is None:
        await message.reply("❌ Kanal aniqlanmadi. Forward yoki @username yuboring.")
        return

    # Bot admin ekanligini tekshirish
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(chat_id, me.id)
        status = getattr(member, "status", "")
        if status not in ("administrator", "creator"):
            await message.reply(
                "❌ Bot bu kanalda admin emas.\n\n"
                "Botni kanalga admin qiling va <b>post yuborish</b> huquqini bering, "
                "keyin qayta urinib ko'ring.",
                parse_mode="HTML",
            )
            return
        # Post yuborish huquqi (Bot API 7.0+ — can_post_messages)
        can_post = getattr(member, "can_post_messages", None)
        if can_post is False:
            await message.reply(
                "⚠️ Bot admin, lekin <b>post yuborish</b> huquqi yo'q. Iltimos bering.",
                parse_mode="HTML",
            )
            return

        chat = await bot.get_chat(chat_id)
        title = chat.title or ""
        username = chat.username or ""
    except Exception as e:
        await message.reply(f"❌ Tekshiruvda xato: <code>{e}</code>", parse_mode="HTML")
        return

    await channels_service.add_channel(
        message.from_user.id, chat_id, title=title, username=username
    )
    await state.clear()

    display = f"@{username}" if username else title or str(chat_id)
    await message.answer(
        f"✅ <b>Kanal qo'shildi:</b>\n\n"
        f"📡 {display}\n"
        f"🆔 <code>{chat_id}</code>\n\n"
        "Endi <b>📡 Kanal boshqaruvi</b> bo'limidan post yuborishingiz mumkin.",
        parse_mode="HTML",
    )


# ===== Kanal ochish (sub-menu) =====


def _channel_menu_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📨 Post yuborish", callback_data=f"ch:post:{chat_id}"),
                InlineKeyboardButton(text="📊 Statistika", callback_data=f"ch:stat:{chat_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 Ro'yxatdan o'chirish", callback_data=f"ch:del:{chat_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="ch:list"),
            ],
        ]
    )


@router.callback_query(F.data.startswith("ch:open:"))
async def cb_channel_open(
    callback: CallbackQuery,
    config: Config,
    channels_service: ChannelsService,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    chat_id = int(callback.data.split(":")[2])
    ch = await channels_service.get_channel(callback.from_user.id, chat_id)
    if not ch:
        await callback.answer("❌ Kanal topilmadi", show_alert=True)
        return
    display = (
        f"@{ch['username']}" if ch.get("username") else (ch.get("title") or str(chat_id))
    )
    text = (
        f"📡 <b>{display}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Chat ID: <code>{chat_id}</code>\n"
    )
    if ch.get("title"):
        text += f"📝 Nom: {ch['title']}\n"
    if ch.get("username"):
        text += f"🔗 Link: https://t.me/{ch['username']}\n"
    text += "\nAmalni tanlang:"

    try:
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=_channel_menu_kb(chat_id),
            disable_web_page_preview=True,
        )
    except Exception:
        await callback.message.answer(
            text, parse_mode="HTML", reply_markup=_channel_menu_kb(chat_id),
            disable_web_page_preview=True,
        )
    await callback.answer()


# ===== Kanal statistikasi =====


@router.callback_query(F.data.startswith("ch:stat:"))
async def cb_channel_stat(
    callback: CallbackQuery,
    bot: Bot,
    config: Config,
    channels_service: ChannelsService,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    chat_id = int(callback.data.split(":")[2])
    try:
        chat = await bot.get_chat(chat_id)
        count = await bot.get_chat_member_count(chat_id)
        admins = await bot.get_chat_administrators(chat_id)
    except Exception as e:
        await callback.answer(f"Xato: {e}", show_alert=True)
        return

    text = (
        f"📊 <b>{chat.title}</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{chat.id}</code>\n"
        f"🔗 Username: {'@' + chat.username if chat.username else '—'}\n"
        f"👥 A'zolar: <b>{count}</b>\n"
        f"🛡 Adminlar: <b>{len(admins)}</b>\n"
        f"🔒 Turi: <code>{chat.type}</code>\n"
    )
    if chat.description:
        desc = chat.description[:200]
        text += f"\n📝 Tavsif: <i>{desc}</i>\n"

    back = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"ch:open:{chat_id}")]
        ]
    )
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back)
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=back)
    await callback.answer()


# ===== Kanalni ro'yxatdan o'chirish =====


@router.callback_query(F.data.startswith("ch:del:"))
async def cb_channel_del(
    callback: CallbackQuery,
    config: Config,
    channels_service: ChannelsService,
    bot: Bot,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    chat_id = int(callback.data.split(":")[2])
    await channels_service.remove_channel(callback.from_user.id, chat_id)
    await callback.answer("✅ Ro'yxatdan o'chirildi", show_alert=False)
    await _show_channels_list(callback, config, channels_service, bot)


# ===== Post yuborish =====


def _post_pre_kb(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"ch:open:{chat_id}")]
        ]
    )


@router.callback_query(F.data.startswith("ch:post:"))
async def cb_channel_post(
    callback: CallbackQuery, config: Config, state: FSMContext
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    chat_id = int(callback.data.split(":")[2])
    await state.set_state(ChannelStates.waiting_post)
    await state.update_data(channel_id=chat_id, buttons=[], pin=False)

    await callback.message.answer(
        "📨 <b>Post yuborish</b>\n\n"
        "Kanalga yubormoqchi bo'lgan xabarni yuboring:\n"
        "• Matn (HTML formatlash qo'llaniladi)\n"
        "• Rasm, video, audio, hujjat, animatsiya\n"
        "• Media-guruh (albom)\n"
        "• Forward\n"
        "• Poll (ovozlar)\n"
        "• Video note / voice\n\n"
        "Xabardan keyin inline URL tugmalar, pin qilish va tasdiqlash taklif qilinadi.\n"
        "/cancel — bekor qilish.",
        parse_mode="HTML",
        reply_markup=_post_pre_kb(chat_id),
    )
    await callback.answer()


@router.message(ChannelStates.waiting_post, Command("cancel"))
async def post_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@router.message(ChannelStates.waiting_post)
async def post_receive(
    message: Message,
    bot: Bot,
    config: Config,
    state: FSMContext,
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    if (message.text or "").strip() in ADMIN_BUTTONS:
        await state.clear()
        await message.answer("ℹ️ Bekor qilindi. Tugmani qayta bosing.")
        return

    data = await state.get_data()
    chat_id = data.get("channel_id")
    if not chat_id:
        await state.clear()
        await message.answer("❌ Kanal aniqlanmadi. Qaytadan boshlang.")
        return

    # Post xabarini saqlaymiz (chat_id + message_id) — keyin copy_message bilan yuboramiz
    await state.update_data(
        src_chat_id=message.chat.id,
        src_message_id=message.message_id,
    )

    preview_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Inline tugma qo'shish", callback_data="ch:post:addbtn"
                ),
            ],
            [
                InlineKeyboardButton(text="📌 Pin qilish: Yo'q", callback_data="ch:post:pin"),
            ],
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="ch:post:send"),
                InlineKeyboardButton(text="❌ Bekor", callback_data=f"ch:open:{chat_id}"),
            ],
        ]
    )
    await message.answer(
        "👆 <b>Post tayyor.</b>\n\n"
        "Qo'shimcha:\n"
        "• Inline URL tugmalar qo'shish\n"
        "• Yuborilgandan keyin pin qilish\n\n"
        "Yoki darhol <b>Yuborish</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=preview_kb,
    )


@router.callback_query(F.data == "ch:post:pin")
async def cb_post_toggle_pin(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    pin = not data.get("pin", False)
    await state.update_data(pin=pin)
    # Yangi klaviatura (pin holati yangilangan)
    chat_id = data.get("channel_id")
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Inline tugma qo'shish", callback_data="ch:post:addbtn")],
            [
                InlineKeyboardButton(
                    text=f"📌 Pin qilish: {'Ha' if pin else 'Yo‘q'}",
                    callback_data="ch:post:pin",
                ),
            ],
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="ch:post:send"),
                InlineKeyboardButton(text="❌ Bekor", callback_data=f"ch:open:{chat_id}"),
            ],
        ]
    )
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass
    await callback.answer("📌" if pin else "—")


@router.callback_query(F.data == "ch:post:addbtn")
async def cb_post_addbtn(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ChannelStates.waiting_buttons)
    await callback.message.answer(
        "🔗 <b>Inline tugmalar</b>\n\n"
        "Formatda yuboring (har qator bitta tugma):\n"
        "<code>Tugma matni | https://example.com</code>\n\n"
        "Bir qatorda 2 ta tugma uchun:\n"
        "<code>A | url1 || B | url2</code>\n\n"
        "/skip — tugmasiz davom etish.\n"
        "/cancel — butunlay bekor qilish.",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ChannelStates.waiting_buttons, Command("cancel"))
async def post_btn_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


def _parse_buttons(text: str) -> list[list[dict[str, str]]]:
    """Matnni inline tugmalarga parse qilish."""
    rows: list[list[dict[str, str]]] = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        btns: list[dict[str, str]] = []
        # "A | url1 || B | url2"
        for part in line.split("||"):
            part = part.strip()
            if "|" not in part:
                continue
            label, url = part.split("|", 1)
            label = label.strip()
            url = url.strip()
            if label and url.startswith(("http://", "https://", "tg://")):
                btns.append({"text": label, "url": url})
        if btns:
            rows.append(btns)
    return rows


@router.message(ChannelStates.waiting_buttons, Command("skip"))
async def post_btn_skip(message: Message, state: FSMContext) -> None:
    await state.set_state(ChannelStates.waiting_post)
    data = await state.get_data()
    chat_id = data.get("channel_id")
    await _reshow_confirm(message, chat_id, data.get("pin", False))


@router.message(ChannelStates.waiting_buttons, F.text)
async def post_btn_receive(message: Message, state: FSMContext) -> None:
    rows = _parse_buttons(message.text or "")
    if not rows:
        await message.reply(
            "❌ Hech qanday tugma aniqlanmadi. Format: <code>Matn | URL</code>",
            parse_mode="HTML",
        )
        return
    await state.update_data(buttons=rows)
    await state.set_state(ChannelStates.waiting_post)
    data = await state.get_data()
    chat_id = data.get("channel_id")
    await message.answer(f"✅ {sum(len(r) for r in rows)} ta tugma qo'shildi.")
    await _reshow_confirm(message, chat_id, data.get("pin", False))


async def _reshow_confirm(message: Message, chat_id: int, pin: bool) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Inline tugmalarni qayta o'zgartirish", callback_data="ch:post:addbtn")],
            [
                InlineKeyboardButton(
                    text=f"📌 Pin qilish: {'Ha' if pin else 'Yo‘q'}",
                    callback_data="ch:post:pin",
                ),
            ],
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="ch:post:send"),
                InlineKeyboardButton(text="❌ Bekor", callback_data=f"ch:open:{chat_id}"),
            ],
        ]
    )
    await message.answer(
        "👇 <b>Tasdiqlash</b>\n\nKanalga yuborishga tayyor.",
        parse_mode="HTML",
        reply_markup=kb,
    )


@router.callback_query(F.data == "ch:post:send")
async def cb_post_send(
    callback: CallbackQuery,
    bot: Bot,
    config: Config,
    state: FSMContext,
) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer("⛔", show_alert=True)
        return
    data = await state.get_data()
    chat_id = data.get("channel_id")
    src_chat_id = data.get("src_chat_id")
    src_message_id = data.get("src_message_id")
    pin = data.get("pin", False)
    button_rows = data.get("buttons", [])

    if not chat_id or not src_chat_id or not src_message_id:
        await callback.answer("❌ Post ma'lumoti yo'q", show_alert=True)
        await state.clear()
        return

    reply_markup: InlineKeyboardMarkup | None = None
    if button_rows:
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=b["text"], url=b["url"]) for b in row]
                for row in button_rows
            ]
        )

    try:
        sent = await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=src_chat_id,
            message_id=src_message_id,
            reply_markup=reply_markup,
        )
    except TelegramBadRequest as e:
        await state.clear()
        await callback.message.answer(f"❌ Yuborishda xato: <code>{e}</code>", parse_mode="HTML")
        await callback.answer()
        return
    except Exception as e:
        await state.clear()
        await callback.message.answer(f"❌ Xato: <code>{e}</code>", parse_mode="HTML")
        await callback.answer()
        return

    pinned_text = ""
    if pin:
        try:
            await bot.pin_chat_message(
                chat_id=chat_id,
                message_id=sent.message_id,
                disable_notification=True,
            )
            pinned_text = "📌 Pin qilindi.\n"
        except Exception as e:
            pinned_text = f"⚠️ Pin qilinmadi: {e}\n"

    await state.clear()
    try:
        await callback.message.edit_text(
            f"✅ <b>Post yuborildi!</b>\n\n"
            f"🆔 Message ID: <code>{sent.message_id}</code>\n"
            f"{pinned_text}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Kanalga qaytish", callback_data=f"ch:open:{chat_id}")]
                ]
            ),
        )
    except Exception:
        pass
    await callback.answer("✅")
