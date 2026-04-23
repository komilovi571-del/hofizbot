"""i18n — ko'p tilli tarjima tizimi.

Foydalanish:
    from bot.i18n import t
    t("welcome", lang="ru")
    t("err_too_many_active", lang="uz", count=3)

Tillar: uz (default), uz_cyrl, ru, en
"""

import logging
from typing import Any

from bot.i18n.en import LANG as EN
from bot.i18n.ru import LANG as RU
from bot.i18n.uz import LANG as UZ
from bot.i18n.uz_cyrl import LANG as UZ_CYRL

logger = logging.getLogger(__name__)

# Qo'llab-quvvatlanadigan tillar
SUPPORTED_LANGS = ["uz", "uz_cyrl", "ru", "en"]
DEFAULT_LANG = "uz"

# Til kodlari → dict
_TRANSLATIONS: dict[str, dict[str, str]] = {
    "uz": UZ,
    "uz_cyrl": UZ_CYRL,
    "ru": RU,
    "en": EN,
}

# Til nomlari (UI'da ko'rsatish uchun)
LANG_NAMES: dict[str, str] = {
    "uz": "🇺🇿 O'zbek",
    "uz_cyrl": "🇺🇿 Ўзбек",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}


def t(key: str, lang: str | None = None, **kwargs: Any) -> str:
    """Kalitga mos tarjimani qaytarish.

    Args:
        key: Tarjima kaliti (masalan, "welcome").
        lang: Til kodi. None yoki noma'lum bo'lsa DEFAULT_LANG ishlatiladi.
        **kwargs: format() uchun qiymatlar (masalan, count=3).

    Returns:
        Tarjima qilingan matn. Kalit topilmasa kalit nomi qaytariladi (debug).
    """
    if not lang or lang not in _TRANSLATIONS:
        lang = DEFAULT_LANG

    table = _TRANSLATIONS.get(lang, _TRANSLATIONS[DEFAULT_LANG])
    template = table.get(key)

    # Fallback: default til'dan olishga urinish
    if template is None and lang != DEFAULT_LANG:
        template = _TRANSLATIONS[DEFAULT_LANG].get(key)

    if template is None:
        logger.warning(f"i18n: kalit topilmadi — '{key}' (lang={lang})")
        return f"[{key}]"

    if not kwargs:
        return template

    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError) as e:
        logger.warning(f"i18n format xatosi: key={key}, lang={lang}, error={e}")
        return template


def normalize_lang(code: str | None) -> str:
    """Foydalanuvchi til kodini normalizatsiya qilish.

    Telegram language_code bo'yicha (uz, uz-cyrl, ru, en, en-US, ...) mos til'ni tanlash.
    """
    if not code:
        return DEFAULT_LANG
    code = code.lower().replace("-", "_")
    if code in _TRANSLATIONS:
        return code
    # Til prefiksi bo'yicha (en_us → en)
    prefix = code.split("_")[0]
    if prefix in _TRANSLATIONS:
        return prefix
    return DEFAULT_LANG


__all__ = ["t", "normalize_lang", "SUPPORTED_LANGS", "DEFAULT_LANG", "LANG_NAMES"]
