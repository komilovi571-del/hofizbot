"""O'zbek tili (lotin) — default til."""

LANG = {
    # ===== Language selector =====
    "lang_choose": "🌐 <b>Tilni tanlang / Выберите язык / Choose language:</b>",
    "lang_changed": "✅ Til o'zgartirildi: <b>🇺🇿 O'zbek</b>",
    "lang_name": "🇺🇿 O'zbek",

    # ===== Start / Help =====
    "welcome": (
        "🔥 Assalomu alaykum. @hofizbot ga Xush kelibsiz. "
        "Bot orqali quyidagilarni yuklab olishingiz mumkin:\n\n"
        "• Instagram — post va IGTV + audio bilan;\n"
        "• TikTok — suv belgisiz video + audio bilan;\n"
        "• Snapchat — suv belgisiz video + audio bilan;\n"
        "• Likee — suv belgisiz video + audio bilan;\n"
        "• Pinterest — suv belgisiz video va rasmlar + audio bilan;\n\n"
        "Shazam funksiya:\n"
        "• Qo'shiq nomi yoki ijrochi ismi\n"
        "• Qo'shiq matni\n"
        "• Ovozli xabar\n"
        "• Video\n"
        "• Audio\n"
        "• Video xabar\n\n"
        "🚀 Yuklab olmoqchi bo'lgan videoga havolani yuboring!\n"
        "😎 Bot guruhlarda ham ishlay oladi!"
    ),
    "help": (
        "📖 <b>Yordam</b>\n\n"
        "<b>📥 Video yuklash:</b>\n"
        "Havolani yuboring → \"🎬 Video\" tugmasini bosing → Sifat tanlang\n\n"
        "<b>🎵 Musiqa yuklash:</b>\n"
        "Havolani yuboring → \"🎵 Musiqa\" tugmasini bosing\n\n"
        "<b>🔍 Musiqa qidirish:</b>\n"
        "Qo'shiq nomi yoki san'atkor ismini yozing\n\n"
        "<b>🎵 Inline rejim:</b>\n"
        "<code>@hofizbot qo'shiq nomi</code>\n\n"
        "<b>🔍 Shazam:</b>\n"
        "Audio, voice, video yoki video note yuboring\n\n"
        "<b>⚙️ Buyruqlar:</b>\n"
        "/start — Bosh menyu\n"
        "/lang — Tilni o'zgartirish\n"
        "/help — Yordam\n"
        "/myid — ID raqamingiz"
    ),

    # ===== Start keyboard =====
    "btn_add_to_group": "➕ Guruhga qo'shish",
    "btn_inline_search": "💬 Inline qidiruv",
    "btn_change_lang": "🌐 Tilni o'zgartirish",

    # ===== Errors =====
    "err_no_url": (
        "❌ Xabaringizda havola topilmadi.\n\n"
        "📎 YouTube, Instagram, TikTok, Facebook yoki Twitter havolasini yuboring."
    ),
    "err_unsupported": (
        "❌ Bu platforma qo'llab-quvvatlanmaydi.\n\n"
        "✅ Qo'llab-quvvatlanadigan platformalar:\n"
        "• YouTube\n• Instagram\n• TikTok\n• Facebook\n• Twitter/X\n"
        "• Pinterest\n• Likee\n• Snapchat\n• Reddit\n• Spotify"
    ),
    "err_rate_limit": "⏱ Juda ko'p so'rov yubordingiz. Biroz kuting.",
    "err_too_many_active": "⚠️ Siz allaqachon {count} ta fayl yuklamoqdasiz. Kuting.",
    "err_ig_blocked": (
        "⏱ Instagram vaqtincha bloklab qo'ydi (rate-limit).\n"
        "• 1-2 daqiqadan so'ng qayta urinib ko'ring\n"
        "• Yoki boshqa platforma havolasini yuboring"
    ),
    "err_login_required": "🔒 Bu kontent login talab qiladi yoki shaxsiy.",
    "err_not_available": "❌ Kontent mavjud emas yoki o'chirilgan.",
    "err_private": "🔒 Shaxsiy kontent.",
    "err_geo": "🌍 Sizning hududingizda mavjud emas.",
    "err_file_too_large": "❌ Fayl juda katta ({size})!\n\nMaksimal: {max_size}",
    "err_retry_or_other": "🔁 Qaytadan urinib ko'ring yoki boshqa havola yuboring.",
    "err_generic": "❌ Kutilmagan xato: {error}",
    "err_banned": "🚫 Siz ban qilingansiz.",

    # ===== Download status =====
    "dl_detected": "✅ <b>{platform}</b> havolasi aniqlandi!\n\nYuklab olish turini tanlang:",
    "dl_in_progress": "⏳ <b>Yuklab olinmoqda...</b>\n\n⚡ 16 ta parallel ulanish\n📊 0%",
    "dl_progress": "📥 <b>Yuklanmoqda:</b> {progress}%\n{bar}\n📦 {downloaded} / {total}",
    "dl_compressing": "🗜 <b>Fayl katta ({size}), siqilmoqda...</b>\n\n⏱ Yuklab olish: {time}s\n📦 ffmpeg bilan siqilmoqda...",
    "dl_converting": "🔄 <b>Video formatga moslashtirildi</b>",
    "dl_uploading": "📤 <b>Telegramga yuborilmoqda...</b>\n\n📁 {size} | ⏱ {time}s da yuklandi",
    "dl_cached": "⚡ <b>Cache-dan yuborilmoqda...</b> (0 soniya!)",
    "dl_cancelled": "❌ Bekor qilindi.",
    "dl_success_video": "🎬 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}s",
    "dl_success_audio": "🎵 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}s",
    "dl_cached_video": "🎬 {title}\n⚡ Cache-dan yuborildi",
    "dl_cached_audio": "🎵 {title}\n⚡ Cache-dan yuborildi",

    # ===== Format selection =====
    "fmt_choose": "Yuklab olish turini tanlang:",
    "fmt_video": "🎬 Video",
    "fmt_audio": "🎵 Musiqa (MP3)",
    "fmt_cancel": "❌ Bekor qilish",
    "quality_choose": "📺 Video sifatini tanlang:",
    "quality_back": "⬅️ Orqaga",

    # ===== Shazam =====
    "shazam_analyzing": "🎵 <b>Musiqa aniqlanmoqda...</b>\n\n🔍 Shazam orqali qidirilmoqda...",
    "shazam_found": "🎵 <b>Videodagi qo'shiq aniqlandi:</b>\n🎤 <b>{artist}</b>\n🎶 <i>{title}</i>",
    "shazam_not_found": "❌ <b>Qo'shiq aniqlanmadi</b>\n\n{reason}",
    "shazam_album": "💿 Albom: {album}",
    "shazam_year": "📅 Yil: {year}",
    "shazam_genre": "🏷 Janr: {genre}",
    "shazam_btn_download_song": "⬇️ Qo'shiqni yuklab olish",
    "shazam_btn_download_music": "🎵 Musiqani yuklab olish",
    "shazam_btn_shazam": "🔗 Shazam",
    "shazam_downloading": "🎵 <b>Yuklab olinmoqda...</b>\n\n🔍 <b>{artist} — {title}</b>\n📥 YouTube'dan qidirilmoqda...",
    "shazam_download_failed": "❌ <b>Qo'shiq topilmadi</b>\n\nYouTube'dan \"{query}\" topilmadi.",
    "shazam_stale": "❌ Ma'lumot eskirgan. Qaytadan audio yuboring.",

    # ===== Cache / generic =====
    "cached_from_cache": "⚡ Cache-dan yuborildi",
    "video_uploading_in_progress": "Yuklanmoqda...",

    # ===== Stats command =====
    "stats_title": "📊 <b>Bot Statistikasi</b>",
    "stats_cache_status": "📦 Cache: {status}",
    "stats_cached_items": "🗂 Saqlangan fayllar: {count}",
    "stats_memory": "💾 Xotira: {memory}",
    "stats_no_cache": "📊 <b>Bot Statistikasi</b>\n\nCache ulanmagan.",

    # ===== My ID =====
    "myid_text": "🆔 Sizning Telegram ID: <code>{id}</code>",

    # ===== Search =====
    "search_prompt": "🔍 Qidirilmoqda: <b>{query}</b>",
    "search_no_results": "❌ Hech narsa topilmadi.",
    "search_results_title": "🔍 <b>Natijalar:</b> {query}",
}
