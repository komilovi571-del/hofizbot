# 🚀 Media Downloader Bot

Ijtimoiy tarmoqlardan video va musiqa yuklab beruvchi **超 tezkor** Telegram bot.

## ⚡ Tezlik optimizatsiyalari

| Texnologiya | Tezlashtirish |
|---|---|
| **aria2c** (16 parallel connections) | 3-10x tezroq yuklab olish |
| **Redis file_id cache** | Takroriy so'rovlar = 0 soniya |
| **yt-dlp Python API** | Subprocess o'rniga in-process (50-200ms tejash) |
| **uvloop** | 2x tezroq event loop (Linux) |
| **tmpfs RAM disk** | Disk I/O yo'q |
| **Local Bot API Server** | 2GB gacha fayl yuborish |

## 📱 Qo'llab-quvvatlanadigan platformalar

- YouTube (video, shorts, playlist)
- Instagram (reels, stories, posts)
- TikTok (video, stories)
- Facebook (video, reels)
- Twitter/X (video)
- **1700+ boshqa saytlar** (yt-dlp orqali)

## 🛠 O'rnatish

### 1. Oddiy ishga tushirish

```bash
# Reponi klonlash
git clone <repo-url>
cd media-downloader-bot

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Kutubxonalar
pip install -r requirements.txt

# Tizim dasturlari (Linux)
sudo apt install aria2 ffmpeg

# Sozlamalar
cp .env.example .env
# .env faylini to'ldiring

# Ishga tushirish
python -m bot
```

### 2. Docker bilan ishga tushirish (tavsiya etiladi)

```bash
# .env faylini sozlash
cp .env.example .env
nano .env  # BOT_TOKEN va boshqalarni kiriting

# Docker compose bilan ishga tushirish
docker compose up -d

# Loglarni ko'rish
docker compose logs -f bot
```

### 3. Railway.app orqali deploy qilish

Railway — eng oson cloud variant: GitHub'dan to'g'ridan-to'g'ri deploy, Redis plugin va
`REDIS_URL` avtomatik inject qilinadi.

**Qadamlar:**

1. https://railway.app ga kiring va "New Project" → "Deploy from GitHub repo" tanlang.
2. Reponi ulang — Railway `Dockerfile` + `railway.toml` ni avtomatik topadi.
3. Xuddi shu loyihaga **Redis** plugin qo'shing ("Add Plugin" → "Redis"). U
   `REDIS_URL` ni avtomatik env variable sifatida beradi.
4. Bot servisining **Variables** bo'limiga quyidagilarni qo'shing:
   - `BOT_TOKEN` — @BotFather'dan olingan token
   - `ADMIN_IDS` — sizning Telegram ID (ixtiyoriy)
   - `BOT_MODE=polling` (default — eng oson)
5. Deploy avtomatik boshlanadi. Log'larni Railway UI'dan kuzating — "Polling
   rejimida ishga tushirilmoqda..." chiqsa, bot tayyor.

**Webhook rejimi (ixtiyoriy, tezroq):**

1. Railway'da **Settings → Networking → Generate Domain** bosing.
2. Variables'ga qo'shing:
   - `BOT_MODE=webhook`
   - `WEBHOOK_URL=https://<your-railway-domain>`
   - (`PORT` env var Railway tomonidan avtomatik beriladi, qo'lda kiritish shart emas)
3. Redeploy qiling.

## ⚙️ Sozlamalar (.env)

```env
# Majburiy
BOT_TOKEN=your_bot_token_here

# Redis (Docker ichida avtomatik)
REDIS_URL=redis://localhost:6379/0

# Yuklab olish sozlamalari
MAX_CONCURRENT_DOWNLOADS=20
MAX_PER_USER_DOWNLOADS=3
ARIA2C_CONNECTIONS=16
ARIA2C_SPLIT=16

# Bot ishi rejimi
BOT_MODE=polling          # polling yoki webhook
```

## 📁 Loyiha tuzilishi

```
media-downloader-bot/
├── bot/
│   ├── __init__.py
│   ├── __main__.py          # python -m bot
│   ├── config.py            # Sozlamalar
│   ├── main.py              # Asosiy kirish nuqtasi
│   ├── handlers/
│   │   ├── start.py         # /start, /help, /stats
│   │   └── download.py      # URL qabul qilish va yuklab olish
│   ├── services/
│   │   ├── url_parser.py    # Platform aniqlash
│   │   ├── downloader.py    # yt-dlp + aria2c yuklovchi
│   │   ├── audio_extractor.py  # FFmpeg audio ajratish
│   │   └── cache.py         # Redis kesh servisi
│   ├── keyboards/
│   │   └── inline.py        # Inline tugmalar
│   ├── middlewares/
│   │   └── throttle.py      # Rate limiting
│   └── utils/
│       ├── progress.py      # Yuklab olish progressi
│       └── helpers.py       # Yordamchi funksiyalar
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── .dockerignore
```

## 🔧 Tizim talablari

- **Python** 3.12+
- **aria2c** — tezkor yuklab oluvchi
- **ffmpeg** — audio/video qayta ishlash
- **Redis** — kesh va rate limiting

## 📊 Arxitektura

```
Foydalanuvchi → Telegram API → Bot (aiogram 3.x)
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              URL Parser      Redis Cache     Downloader
              (Platform       (file_id +      (yt-dlp +
               aniqlash)       rate limit)     aria2c)
                                                   │
                                              ┌────┴────┐
                                              │         │
                                          aria2c    ffmpeg
                                        (16 conn)  (audio)
```

## 📝 Litsenziya

MIT License
