"""
Bot konfiguratsiyasi — barcha sozlamalar .env fayldan olinadi.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class BotConfig:
    """Telegram Bot sozlamalari."""
    token: str = ""
    mode: str = "polling"  # "polling" or "webhook"


@dataclass
class WebhookConfig:
    """Webhook sozlamalari."""
    url: str = ""
    host: str = "0.0.0.0"
    port: int = 8443


@dataclass
class RedisConfig:
    """Redis sozlamalari."""
    url: str = "redis://localhost:6379/0"
    cache_ttl: int = 48 * 3600  # 48 soat


@dataclass
class DownloadConfig:
    """Yuklab olish sozlamalari."""
    temp_dir: str = "./tmp"
    max_concurrent: int = 20
    max_per_user: int = 3
    max_file_size: int = 2_147_483_648  # 2GB
    rate_limit_per_minute: int = 5

    # aria2c settings
    aria2c_connections: int = 16
    aria2c_split: int = 16
    aria2c_min_split_size: str = "1M"

    # Cookies fayl (Instagram va boshqa saytlar uchun)
    cookies_file: str = ""

    # Proxy (Cloudflare WARP yoki boshqa proxy)
    proxy: str = ""


@dataclass
class TelegramApiConfig:
    """Telegram API sozlamalari."""
    local_bot_api_url: str = ""  # Bo'sh bo'lsa standart API ishlatiladi


@dataclass
class Config:
    """Asosiy konfiguratsiya."""
    bot: BotConfig = field(default_factory=BotConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    telegram_api: TelegramApiConfig = field(default_factory=TelegramApiConfig)
    admin_ids: list[int] = field(default_factory=list)
    log_level: str = "INFO"


def load_config() -> Config:
    """Konfiguratsiyani .env fayldan yuklash."""
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids: list[int] = []
    for x in admin_ids_str.split(","):
        x = x.strip()
        if not x:
            continue
        try:
            admin_ids.append(int(x))
        except ValueError:
            # Noto'g'ri admin ID sabab bot crash bo'lmasligi kerak
            pass

    config = Config(
        bot=BotConfig(
            token=os.getenv("BOT_TOKEN", ""),
            mode=os.getenv("BOT_MODE", "polling"),
        ),
        webhook=WebhookConfig(
            url=os.getenv("WEBHOOK_URL", ""),
            host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
            # Railway/Heroku/Render — PORT env var avtomatik beriladi
            port=int(os.getenv("PORT") or os.getenv("WEBHOOK_PORT") or "8443"),
        ),
        redis=RedisConfig(
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        ),
        download=DownloadConfig(
            temp_dir=os.getenv("TEMP_DIR", "./tmp"),
            max_concurrent=int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "20")),
            max_per_user=int(os.getenv("MAX_PER_USER_DOWNLOADS", "3")),
            max_file_size=int(os.getenv("MAX_FILE_SIZE", "2147483648")),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "5")),
            aria2c_connections=int(os.getenv("ARIA2C_CONNECTIONS", "16")),
            aria2c_split=int(os.getenv("ARIA2C_SPLIT", "16")),
            aria2c_min_split_size=os.getenv("ARIA2C_MIN_SPLIT_SIZE", "1M"),
            cookies_file=os.getenv("COOKIES_FILE", ""),
            proxy=os.getenv("PROXY_URL", ""),
        ),
        telegram_api=TelegramApiConfig(
            local_bot_api_url=os.getenv("LOCAL_BOT_API_URL", ""),
        ),
        admin_ids=admin_ids,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )

    # Temp directory yaratish
    Path(config.download.temp_dir).mkdir(parents=True, exist_ok=True)

    return config
