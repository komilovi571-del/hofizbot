"""
Start Handler — /start va /help buyruqlari.
"""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router(name="start")


WELCOME_TEXT = """
🎬 <b>Media Downloader Bot</b>

Ijtimoiy tarmoqlardan video va musiqa yuklab beruvchi eng tez bot!

⚡ <b>Tezlik:</b> aria2c bilan 16 ta parallel ulanish — 3-10x tezroq yuklash!

📎 <b>Platformalar:</b>
• 🎬 YouTube  • 📸 Instagram  • 🎵 TikTok
• 📘 Facebook  • 🐦 Twitter/X
• 📌 Pinterest  • ❤️ Likee  • 👻 Snapchat
• 🟠 Reddit  • 🎧 Spotify

📥 <b>Ishlatish:</b>
1️⃣ Video/musiqa havolasini yuboring
2️⃣ Yoki qo‘shiq nomini yozing — topib beraman!
3️⃣ Audio/voice/video yuboring — Shazam bilan aniqlash

🎵 <b>Inline rejim:</b> @hofizbot qo‘shiq nomi

/help — Yordam
/admin — Admin panel
/myid — Telegram ID
"""

HELP_TEXT = """
📖 <b>Yordam</b>

<b>📥 Video yuklash:</b>
Havolani yuboring → "🎬 Video" tugmasini bosing → Sifat tanlang

<b>🎵 Musiqa yuklash:</b>
Havolani yuboring → "🎵 Musiqa" tugmasini bosing
Yoki video yuklagandan keyin "🎵 Musiqani yuklab olish" tugmasini bosing

<b>🔍 Musiqa qidirish:</b>
Qo'shiq nomi yoki san'atkor ismini yozing → natijalardan tanlang

<b>🎵 Inline rejim:</b>
Har qanday chatda <code>@hofizbot qo'shiq nomi</code> yozing

<b>🔍 Shazam (musiqa aniqlash):</b>
Audio, voice, video yoki video note yuboring
Bot Shazam orqali qo'shiqni aniqlaydi va yuklab beradi

<b>📎 Platformalar:</b>
• YouTube • Instagram • TikTok
• Facebook • Twitter/X • Pinterest
• Likee • Snapchat • Reddit • Spotify

<b>⚠️ Cheklovlar:</b>
• Daqiqada 5 ta so'rov
• Bir vaqtda 3 ta yuklash
• Max fayl: 2GB
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Bot ishga tushirilganda."""
    await message.answer(WELCOME_TEXT, parse_mode="HTML")


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
