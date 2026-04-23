# ==========================================
#  Media Downloader Bot — Dockerfile
#  Python 3.12 + aria2c + ffmpeg + yt-dlp
# ==========================================

FROM python:3.12-slim AS base

# Metadata
LABEL maintainer="Media Downloader Bot"
LABEL description="Telegram bot for downloading videos/audio from social media"

# Tizim o'zgaruvchilari
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Tizim dasturlari o'rnatish
RUN apt-get update && apt-get install -y --no-install-recommends \
    aria2 \
    ffmpeg \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Ishchi papka
WORKDIR /app

# Python kutubxonalarni o'rnatish (kesh uchun avval)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot kodini ko'chirish
COPY bot/ ./bot/
COPY run.py .
COPY data/ ./data/

# Temp + data directory
RUN mkdir -p /tmp/media-bot /app/data

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import yt_dlp; print('OK')" || exit 1

# Portlar (webhook uchun)
EXPOSE 8443

# Ishga tushirish
CMD ["python", "run.py"]
