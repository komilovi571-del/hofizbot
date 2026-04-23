"""
URL Parser — foydalanuvchi yuborgan havoladan platformani aniqlash.

Qo'llab-quvvatlanadigan platformalar:
- YouTube (youtube.com, youtu.be, music.youtube.com)
- Instagram (instagram.com, instagr.am)
- TikTok (tiktok.com, vm.tiktok.com)
- Facebook (facebook.com, fb.watch, fb.com)
- Twitter/X (twitter.com, x.com, t.co)
- Pinterest (pinterest.com, pin.it)
- Likee (likee.video, l.likee.video)
- Snapchat (snapchat.com, story.snapchat.com)
- Reddit (reddit.com)
- Spotify (open.spotify.com)
"""

import re
from enum import Enum
from dataclasses import dataclass


class Platform(Enum):
    """Qo'llab-quvvatlanadigan platformalar."""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    PINTEREST = "pinterest"
    LIKEE = "likee"
    SNAPCHAT = "snapchat"
    REDDIT = "reddit"
    SPOTIFY = "spotify"
    UNKNOWN = "unknown"


# Har bir platforma uchun regex patternlar
PLATFORM_PATTERNS: dict[Platform, re.Pattern] = {
    Platform.YOUTUBE: re.compile(
        r'(?:https?://)?(?:www\.|m\.)?'
        r'(?:youtube\.com/(?:watch\?.*v=|shorts/|embed/|v/|live/|playlist\?|clip/)|'
        r'youtu\.be/|'
        r'music\.youtube\.com/watch\?)',
        re.IGNORECASE,
    ),
    Platform.INSTAGRAM: re.compile(
        r'(?:https?://)?(?:www\.)?'
        r'(?:instagram\.com|instagr\.am)'
        r'/(?:p|reel|reels|tv|stories)/',
        re.IGNORECASE,
    ),
    Platform.TIKTOK: re.compile(
        r'(?:https?://)?(?:www\.|vm\.|vt\.)?'
        r'tiktok\.com/',
        re.IGNORECASE,
    ),
    Platform.FACEBOOK: re.compile(
        r'(?:https?://)?(?:www\.|m\.|web\.)?'
        r'(?:facebook\.com|fb\.com|fb\.watch)'
        r'(?:/(?:watch|video|reel|share))?',
        re.IGNORECASE,
    ),
    Platform.TWITTER: re.compile(
        r'(?:https?://)?(?:www\.|mobile\.)?'
        r'(?:twitter\.com|x\.com|t\.co)/',
        re.IGNORECASE,
    ),
    Platform.PINTEREST: re.compile(
        r'(?:https?://)?(?:www\.)?'
        r'(?:pinterest\.com/pin/|pin\.it/)',
        re.IGNORECASE,
    ),
    Platform.LIKEE: re.compile(
        r'(?:https?://)?(?:www\.)?'
        r'(?:l\.)?likee\.video/',
        re.IGNORECASE,
    ),
    Platform.SNAPCHAT: re.compile(
        r'(?:https?://)?(?:www\.)?'
        r'(?:story\.)?snapchat\.com/(?:spotlight|discover|add|story)',
        re.IGNORECASE,
    ),
    Platform.REDDIT: re.compile(
        r'(?:https?://)?(?:www\.)?'
        r'reddit\.com/r/.+/comments/',
        re.IGNORECASE,
    ),
    Platform.SPOTIFY: re.compile(
        r'(?:https?://)?'
        r'open\.spotify\.com/(?:track|album|playlist)/',
        re.IGNORECASE,
    ),
}

# Umumiy URL aniqlash uchun pattern
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\']+|'
    r'(?:www\.)[^\s<>"\']+',
    re.IGNORECASE,
)


@dataclass
class ParsedURL:
    """Aniqlangan URL ma'lumotlari."""
    url: str
    platform: Platform
    is_valid: bool = True
    error_message: str = ""


def extract_urls(text: str) -> list[str]:
    """Matndan barcha URL larni ajratib olish."""
    return URL_PATTERN.findall(text)


def detect_platform(url: str) -> Platform:
    """URL dan platformani aniqlash."""
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return platform
    return Platform.UNKNOWN


def parse_url(text: str) -> ParsedURL:
    """
    Foydalanuvchi xabaridan URL ni topish va platformani aniqlash.

    Returns:
        ParsedURL — aniqlangan URL va platforma ma'lumotlari.
    """
    urls = extract_urls(text)

    if not urls:
        return ParsedURL(
            url="",
            platform=Platform.UNKNOWN,
            is_valid=False,
            error_message="❌ Xabaringizda havola topilmadi.\n\n"
                          "📎 YouTube, Instagram, TikTok, Facebook yoki Twitter havolasini yuboring.",
        )

    url = urls[0]

    # URL ni to'g'rilash (https qo'shish)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    platform = detect_platform(url)

    if platform == Platform.UNKNOWN:
        return ParsedURL(
            url=url,
            platform=Platform.UNKNOWN,
            is_valid=False,
            error_message="❌ Bu platforma qo'llab-quvvatlanmaydi.\n\n"
                          "✅ Qo'llab-quvvatlanadigan platformalar:\n"
                          "• YouTube\n• Instagram\n• TikTok\n• Facebook\n• Twitter/X\n"
                          "• Pinterest\n• Likee\n• Snapchat\n• Reddit\n• Spotify",
        )

    # Kanonik URL \u2014 cache hit rate'ni oshirish uchun
    normalized = normalize_url(url, platform)
    return ParsedURL(url=normalized, platform=platform)


# Platforma nomlari va emoji lari
PLATFORM_INFO: dict[Platform, dict[str, str]] = {
    Platform.YOUTUBE: {"name": "YouTube", "emoji": "🎬"},
    Platform.INSTAGRAM: {"name": "Instagram", "emoji": "📸"},
    Platform.TIKTOK: {"name": "TikTok", "emoji": "🎵"},
    Platform.FACEBOOK: {"name": "Facebook", "emoji": "📘"},
    Platform.TWITTER: {"name": "Twitter/X", "emoji": "🐦"},
    Platform.PINTEREST: {"name": "Pinterest", "emoji": "📌"},
    Platform.LIKEE: {"name": "Likee", "emoji": "❤️"},
    Platform.SNAPCHAT: {"name": "Snapchat", "emoji": "👻"},
    Platform.REDDIT: {"name": "Reddit", "emoji": "🟠"},
    Platform.SPOTIFY: {"name": "Spotify", "emoji": "🎧"},
    Platform.UNKNOWN: {"name": "Noma'lum", "emoji": "❓"},
}


def get_platform_display(platform: Platform) -> str:
    """Platforma nomi va emoji sini qaytarish."""
    info = PLATFORM_INFO.get(platform, PLATFORM_INFO[Platform.UNKNOWN])
    return f"{info['emoji']} {info['name']}"


# =====================================================================
#  URL normalizer \u2014 cache hit rate'ni oshirish uchun kanonik URL
# =====================================================================

_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|v/|live/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)
_IG_SHORT_RE = re.compile(
    r"instagram\.com/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_TWITTER_RE = re.compile(
    r"(?:twitter\.com|x\.com)/[^/]+/status/(\d+)",
    re.IGNORECASE,
)
_TIKTOK_RE = re.compile(
    r"tiktok\.com/(?:@[^/]+/video|v)/(\d+)",
    re.IGNORECASE,
)


def normalize_url(url: str, platform: Platform) -> str:
    """
    URL ni kanonik shaklga keltirish \u2014 cache kalitlari mos keladi.

    Misol:
        https://youtu.be/abc?t=30       \u2192 https://www.youtube.com/watch?v=abc
        https://www.youtube.com/watch?v=abc&list=... \u2192 https://www.youtube.com/watch?v=abc
        https://m.instagram.com/p/XYZ/?igsh=... \u2192 https://www.instagram.com/p/XYZ/
    """
    if not url:
        return url
    try:
        if platform == Platform.YOUTUBE:
            m = _YT_ID_RE.search(url)
            if m:
                return f"https://www.youtube.com/watch?v={m.group(1)}"
        elif platform == Platform.INSTAGRAM:
            m = _IG_SHORT_RE.search(url)
            if m:
                # /reel/ va /p/ ni bir xil kalitga aylantirmaymiz \u2014 format farqli
                kind = "reel" if "/reel" in url.lower() else "p"
                return f"https://www.instagram.com/{kind}/{m.group(1)}/"
        elif platform == Platform.TWITTER:
            m = _TWITTER_RE.search(url)
            if m:
                return f"https://x.com/i/status/{m.group(1)}"
        elif platform == Platform.TIKTOK:
            m = _TIKTOK_RE.search(url)
            if m:
                return f"https://www.tiktok.com/video/{m.group(1)}"
    except Exception:
        pass
    # Fallback: query string'dagi tracking parametrlarini olib tashlash
    return re.sub(r"[?&](utm_[^=]+|igsh|si|fbclid|feature|list|t|start)=[^&]*", "", url).rstrip("?&")
