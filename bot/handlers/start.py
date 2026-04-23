"""
Start Handler — /start va /help buyruqlari.
"""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

router = Router(name="start")


WELCOME_TEXT = """🔥 Assalomu alaykum. @hofizbot ga Xush kelibsiz. Bot orqali quyidagilarni yuklab olishingiz mumkin:

• Instagram — post va IGTV + audio bilan;
• TikTok — suv belgisiz video + audio bilan;
• Snapchat — suv belgisiz video + audio bilan;
• Likee — suv belgisiz video + audio bilan;
• Pinterest — suv belgisiz video va rasmlar + audio bilan;

Shazam funksiya:
• Qo‘shiq nomi yoki ijrochi ismi
• Qo‘shiq matni
• Ovozli xabar
• Video
• Audio
• Video xabar

🚀 Yuklab olmoqchi bo‘lgan videoga havolani yuboring!
😎 Bot guruhlarda ham ishlay oladi!"""

HELP_TEXT = """📖 <b>Yordam</b>

<b>📥 Video yuklash:</b>
Havolani yuboring → "🎬 Video" tugmasini bosing → Sifat tanlang

<b>🎵 Musiqa yuklash:</b>
Havolani yuboring → "🎵 Musiqa" tugmasini bosing

<b>🔍 Musiqa qidirish:</b>
Qo‘shiq nomi yoki san'atkor ismini yozing

<b>🎵 Inline rejim:</b>
<code>@hofizbot qo‘shiq nomi</code>

<b>🔍 Shazam:</b>
Audio, voice, video yoki video note yuboring

<b>⚠️ Cheklovlar:</b>
• Daqiqada 5 ta so‘rov
• Bir vaqtda 3 ta yuklash
• Max fayl: 50MB (Telegram limiti)
"""


def _start_keyboard() -> InlineKeyboardMarkup:
    """Start xabari uchun inline klaviatura — guruhga qo‘shish tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Guruhga qo‘shish",
                    url="https://t.me/hofizbot?startgroup=true",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Inline qidiruv",
                    switch_inline_query_current_chat="",
                ),
            ],
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Bot ishga tushirilganda."""
    await message.answer(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=_start_keyboard(),
        disable_web_page_preview=True,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """/help buyrug'i."""
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message, cache_service=None) -> None:
    """/stats buyrug'i — bot statistikasi."""
    if cache_service:
        stats = await cache_service.get_stats()
        text = (
            "📊 <b>Bot Statistikasi</b>\n\n"
            f"📦 Cache: {stats.get('status', 'N/A')}\n"
            f"🗂 Saqlangan fayllar: {stats.get('cached_items', 0)}\n"
            f"💾 Xotira: {stats.get('memory_used', 'N/A')}\n"
        )
    else:
        text = "📊 <b>Bot Statistikasi</b>\n\nCache ulanmagan."

    await message.answer(text, parse_mode="HTML")
