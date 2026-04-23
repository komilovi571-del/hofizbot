"""
Inline Keyboard — foydalanuvchiga video/audio tanlash tugmalari.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_format_keyboard(url_hash: str) -> InlineKeyboardMarkup:
    """
    Video yoki audio tanlash uchun asosiy keyboard.

    url_hash — URL ning qisqa hash-i (callback data-da ishlatiladi).
    """
    builder = InlineKeyboardBuilder()

    # Video sifat tugmalari
    builder.row(
        InlineKeyboardButton(
            text="🎬 Video yuklab olish",
            callback_data=f"quality:{url_hash}",
        )
    )

    # Audio tugmasi
    builder.row(
        InlineKeyboardButton(
            text="🎵 Musiqa yuklab olish (MP3)",
            callback_data=f"audio:mp3:{url_hash}",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="🎧 Musiqa yuklab olish (Opus — sifatliroq)",
            callback_data=f"audio:opus:{url_hash}",
        ),
    )

    return builder.as_markup()


def get_quality_keyboard(url_hash: str) -> InlineKeyboardMarkup:
    """Video sifatini tanlash keyboard-i."""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📱 360p", callback_data=f"dl:video:360:{url_hash}"),
        InlineKeyboardButton(text="📺 480p", callback_data=f"dl:video:480:{url_hash}"),
    )
    builder.row(
        InlineKeyboardButton(text="💻 720p HD", callback_data=f"dl:video:720:{url_hash}"),
        InlineKeyboardButton(text="🖥 1080p FHD", callback_data=f"dl:video:1080:{url_hash}"),
    )
    builder.row(
        InlineKeyboardButton(text="⚡ Eng yaxshi sifat", callback_data=f"dl:video:best:{url_hash}"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"back:{url_hash}"),
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
    )
    return builder.as_markup()


def get_back_keyboard(url_hash: str) -> InlineKeyboardMarkup:
    """Orqaga qaytish tugmasi."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ Boshqa format tanlash", callback_data=f"back:{url_hash}"),
    )
    return builder.as_markup()
