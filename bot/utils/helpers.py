"""
Yordamchi funksiyalar.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)


def check_dependencies() -> dict[str, bool]:
    """Barcha kerakli dasturlar o'rnatilganligini tekshirish."""
    deps = {}

    # ffmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, timeout=5,
        )
        deps["ffmpeg"] = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        deps["ffmpeg"] = False

    # aria2c
    try:
        result = subprocess.run(
            ["aria2c", "--version"],
            capture_output=True, timeout=5,
        )
        deps["aria2c"] = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        deps["aria2c"] = False

    # yt-dlp
    try:
        import yt_dlp
        deps["yt-dlp"] = True
    except ImportError:
        deps["yt-dlp"] = False

    return deps


def print_startup_banner(deps: dict[str, bool]) -> None:
    """Bot ishga tushganda banner chiqarish."""
    banner = """
╔══════════════════════════════════════════════════╗
║     🎬 Media Downloader Bot                      ║
║     ⚡ Powered by yt-dlp + aria2c                ║
║     📥 YouTube • Instagram • TikTok • FB • X     ║
╚══════════════════════════════════════════════════╝
"""
    print(banner)

    for dep, installed in deps.items():
        status = "✅" if installed else "❌"
        print(f"  {status} {dep}")

    print()

    missing = [d for d, ok in deps.items() if not ok]
    if missing:
        logger.warning(f"⚠️ O'rnatilmagan dasturlar: {', '.join(missing)}")
        if "aria2c" in missing:
            logger.warning(
                "aria2c o'rnatilmagan! Yuklab olish sekinroq bo'ladi.\n"
                "O'rnatish: sudo apt install aria2 (Linux) / choco install aria2 (Windows)"
            )
        if "ffmpeg" in missing:
            logger.warning(
                "ffmpeg o'rnatilmagan! Audio ajratish ishlamaydi.\n"
                "O'rnatish: sudo apt install ffmpeg (Linux) / choco install ffmpeg (Windows)"
            )
