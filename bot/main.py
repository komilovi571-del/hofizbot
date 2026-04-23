"""
Media Downloader Bot — Asosiy entry point.

Ijtimoiy tarmoqlardan video va musiqa yuklab beruvchi
eng tez Telegram bot.

Ishlatish:
    python -m bot.main

Tezlik optimizatsiyalari:
    - fastdl: 16 ta parallel ulanish (3-10x tezroq)
    - Redis cache: takroriy so'rovlar 0 soniyada
    - uvloop: tezlashtirilgan event loop
    - tmpfs: RAM diskda vaqtinchalik fayllar
    - ProcessPoolExecutor: CPU-bound ishlar alohida process-da
"""

import asyncio
import logging
import os
import base64
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from bot.config import Config, load_config
from bot.handlers import admin, download, inline, shazam, start
from bot.middlewares.throttle import LoggingMiddleware, ThrottleMiddleware
from bot.services.cache import CacheService
from bot.services.downloader import Downloader
from bot.services.stats import StatsService
from bot.utils.helpers import check_dependencies, print_startup_banner

# uvloop — tezlashtirilgan event loop (faqat Linux/macOS)
try:
    import uvloop
    uvloop.install()
except ImportError:
    pass

logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """Logging sozlamalari."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # Ortiqcha loglarni kamaytirish
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("yt_dlp").setLevel(logging.WARNING)


async def on_startup(
    bot: Bot,
    config: Config,
    cache_service: CacheService,
    stats_service: StatsService,
) -> None:
    """Bot ishga tushganda."""
    # Redis ulanish
    await cache_service.connect()

    # Stats debounced flush vazifasini ishga tushirish
    stats_service.start_background_flush()

    # Webhook rejimida webhook o'rnatish
    if config.bot.mode == "webhook" and config.webhook.url:
        await bot.set_webhook(
            url=config.webhook.url,
            drop_pending_updates=True,
        )
        logger.info(f"Webhook o'rnatildi: {config.webhook.url}")

    me = await bot.get_me()
    logger.info(f"🤖 Bot ishga tushdi: @{me.username} ({me.full_name})")


async def on_shutdown(
    bot: Bot,
    config: Config,
    cache_service: CacheService,
    stats_service: StatsService,
) -> None:
    """Bot to'xtaganda."""
    # Stats'ni oxirgi marta saqlash
    await stats_service.stop_background_flush()

    # Redis yopish
    await cache_service.disconnect()

    # Webhook rejimida webhook o'chirish
    if config.bot.mode == "webhook":
        await bot.delete_webhook()

    # Bot sessiyasini yopish (polling/webhook ikkalasida ham)
    try:
        await bot.session.close()
    except Exception:
        pass

    logger.info("Bot to'xtatildi")


async def main() -> None:
    """Asosiy funksiya — botni ishga tushirish."""

    # Konfiguratsiya yuklash
    config = load_config()

    if not config.bot.token:
        print("❌ BOT_TOKEN topilmadi! .env faylda BOT_TOKEN ni belgilang.")
        print("   .env.example faylidan nusxa ko'chiring: cp .env.example .env")
        sys.exit(1)

    # Logging sozlash
    setup_logging(config.log_level)

    # Dependency tekshirish
    deps = check_dependencies()
    print_startup_banner(deps)

    if not deps.get("yt-dlp"):
        print("❌ yt-dlp o'rnatilmagan! pip install yt-dlp")
        sys.exit(1)

    # Cookies env var'dan faylga yozish (Instagram/YouTube rate-limit bypass uchun)
    # COOKIES_B64 — Netscape cookies.txt fayl base64 kodlangan holda
    cookies_b64 = os.getenv("COOKIES_B64", "").strip()
    if cookies_b64 and not config.download.cookies_file:
        try:
            cookies_path = Path(config.download.temp_dir) / "cookies.txt"
            cookies_path.parent.mkdir(parents=True, exist_ok=True)
            cookies_path.write_bytes(base64.b64decode(cookies_b64))
            config.download.cookies_file = str(cookies_path)
            logger.info(f"Cookies env var'dan yozildi: {cookies_path}")
        except Exception as e:
            logger.warning(f"COOKIES_B64 decode xatosi: {e}")

    # ====== Servislar yaratish ======

    # Stats service (JSON file)
    stats_service = StatsService(data_dir="data")

    # Cache service (Redis)
    cache_service = CacheService(
        redis_url=config.redis.url,
        ttl=config.redis.cache_ttl,
    )

    # Downloader (yt-dlp + fastdl)
    downloader = Downloader(
        temp_dir=config.download.temp_dir,
        fastdl_connections=config.download.fastdl_connections,
        fastdl_split=config.download.fastdl_split,
        fastdl_min_split_size=config.download.fastdl_min_split_size,
        max_concurrent=config.download.max_concurrent,
        cookies_file=config.download.cookies_file,
        proxy=config.download.proxy,
    )

    # ====== Bot yaratish ======

    # Session — Local Bot API server yoki standart API
    session = None
    if config.telegram_api.local_bot_api_url:
        local_server = TelegramAPIServer.from_base(
            config.telegram_api.local_bot_api_url,
        )
        session = AiohttpSession(api=local_server)
        logger.info(f"Local Bot API: {config.telegram_api.local_bot_api_url}")

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    # ====== Dispatcher yaratish ======
    dp = Dispatcher()

    # Middleware registratsiyasi
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottleMiddleware(
        rate_limit=config.download.rate_limit_per_minute,
        admin_ids=config.admin_ids,
    ))

    # Router registratsiyasi
    dp.include_router(admin.router)    # Admin — /admin, /user (eng birinchi)
    dp.include_router(start.router)
    dp.include_router(shazam.router)   # Shazam — audio/voice aniqlash
    dp.include_router(inline.router)   # Inline — musiqa qidirish
    dp.include_router(download.router) # Download — URL handler (eng oxirida)

    # Dependency injection — servislarni handler-larga uzatish
    dp["cache_service"] = cache_service
    dp["downloader"] = downloader
    dp["config"] = config
    dp["stats_service"] = stats_service

    # Startup/Shutdown hooks
    async def _on_startup() -> None:
        await on_startup(bot, config, cache_service, stats_service)

    async def _on_shutdown() -> None:
        await on_shutdown(bot, config, cache_service, stats_service)

    dp.startup.register(_on_startup)
    dp.shutdown.register(_on_shutdown)

    # ====== Botni ishga tushirish ======

    if config.bot.mode == "webhook":
        # Webhook rejimi (production uchun)
        from aiohttp import web

        app = web.Application()
        webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_handler.register(app, path="/webhook")
        setup_application(app, dp, bot=bot)

        logger.info(f"Webhook server: {config.webhook.host}:{config.webhook.port}")

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=config.webhook.host, port=config.webhook.port)
        try:
            await site.start()
            # To'xtamasin uchun cheksiz kutamiz
            while True:
                await asyncio.sleep(3600)
        finally:
            await runner.cleanup()
    else:
        # Polling rejimi (development uchun)
        logger.info("Polling rejimida ishga tushirilmoqda...")

        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
                drop_pending_updates=True,
            )
        finally:
            await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot to'xtatildi")
    except Exception as e:
        print(f"❌ Xato: {e}")
        sys.exit(1)
