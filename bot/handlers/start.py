"""Start Handler — /start, /help, /lang, /stats, /myid buyruqlari."""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
)

from bot.i18n import LANG_NAMES, SUPPORTED_LANGS, t
from bot.services.stats import StatsService

logger = logging.getLogger(__name__)

router = Router(name="start")


def _lang_keyboard() -> InlineKeyboardMarkup:
    """Til tanlash klaviaturasi (4 til)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=LANG_NAMES["uz"], callback_data="lang:set:uz"),
                InlineKeyboardButton(text=LANG_NAMES["uz_cyrl"], callback_data="lang:set:uz_cyrl"),
            ],
            [
                InlineKeyboardButton(text=LANG_NAMES["ru"], callback_data="lang:set:ru"),
                InlineKeyboardButton(text=LANG_NAMES["en"], callback_data="lang:set:en"),
            ],
        ]
    )


def _start_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Start xabari uchun inline klaviatura."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("btn_add_to_group", lang),
                    url="https://t.me/hofizbot?startgroup=true",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("btn_inline_search", lang),
                    switch_inline_query_current_chat="",
                ),
                InlineKeyboardButton(
                    text=t("btn_change_lang", lang),
                    callback_data="lang:menu",
                ),
            ],
        ]
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    lang: str = "uz",
    stats_service: StatsService | None = None,
) -> None:
    """Bot ishga tushirilganda.

    Yangi foydalanuvchiga (til saqlamagan) — til tanlash ekrani.
    Aks holda — WELCOME tanlangan tilda.
    """
    user_id = message.from_user.id if message.from_user else 0
    saved_lang = stats_service.get_lang(user_id) if stats_service else None

    # Eski reply-keyboardni (masalan, admin paneldagi "❌ Yopish") tozalash
    try:
        tmp = await message.answer("✅", reply_markup=ReplyKeyboardRemove())
        await tmp.delete()
    except Exception:
        pass

    if not saved_lang:
        await message.answer(
            t("lang_choose", lang),
            parse_mode="HTML",
            reply_markup=_lang_keyboard(),
        )
        return

    await message.answer(
        t("welcome", saved_lang),
        parse_mode="HTML",
        reply_markup=_start_keyboard(saved_lang),
        disable_web_page_preview=True,
    )


@router.message(Command("lang"))
async def cmd_lang(message: Message, lang: str = "uz") -> None:
    """/lang — tilni qayta tanlash."""
    # Eski reply-keyboardni tozalash
    try:
        tmp = await message.answer("🌐", reply_markup=ReplyKeyboardRemove())
        await tmp.delete()
    except Exception:
        pass
    await message.answer(
        t("lang_choose", lang),
        parse_mode="HTML",
        reply_markup=_lang_keyboard(),
    )


@router.callback_query(F.data == "lang:menu")
async def cb_lang_menu(callback: CallbackQuery, lang: str = "uz") -> None:
    """Til tanlash menyusini ko'rsatish."""
    try:
        await callback.message.edit_text(
            t("lang_choose", lang),
            parse_mode="HTML",
            reply_markup=_lang_keyboard(),
        )
    except Exception:
        await callback.message.answer(
            t("lang_choose", lang),
            parse_mode="HTML",
            reply_markup=_lang_keyboard(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("lang:set:"))
async def cb_lang_set(
    callback: CallbackQuery,
    stats_service: StatsService | None = None,
) -> None:
    """Til tanlandi — saqlash va welcome yuborish."""
    code = callback.data.split(":")[2]
    if code not in SUPPORTED_LANGS:
        await callback.answer("Unsupported", show_alert=True)
        return

    user = callback.from_user
    if stats_service and user:
        stats_service.track_user(
            user.id,
            username=user.username or "",
            full_name=user.full_name or "",
        )
        stats_service.set_lang(user.id, code)

    try:
        await callback.message.edit_text(t("lang_changed", code), parse_mode="HTML")
    except Exception:
        pass

    await callback.message.answer(
        t("welcome", code),
        parse_mode="HTML",
        reply_markup=_start_keyboard(code),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str = "uz") -> None:
    """/help buyrug'i."""
    await message.answer(t("help", lang), parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(
    message: Message, cache_service=None, lang: str = "uz"
) -> None:
    """/stats — bot statistikasi (keshi)."""
    if cache_service:
        stats = await cache_service.get_stats()
        text = (
            f"{t('stats_title', lang)}\n\n"
            f"{t('stats_cache_status', lang, status=stats.get('status', 'N/A'))}\n"
            f"{t('stats_cached_items', lang, count=stats.get('cached_items', 0))}\n"
            f"{t('stats_memory', lang, memory=stats.get('memory_used', 'N/A'))}\n"
        )
    else:
        text = t("stats_no_cache", lang)

    await message.answer(text, parse_mode="HTML")


@router.message(Command("myid"))
async def cmd_myid(message: Message, lang: str = "uz") -> None:
    """Foydalanuvchi ID sini ko'rsatish."""
    await message.reply(
        t("myid_text", lang, id=message.from_user.id),
        parse_mode="HTML",
    )
