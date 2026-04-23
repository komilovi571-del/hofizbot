"""English language."""

LANG = {
    "lang_choose": "🌐 <b>Choose language / Tilni tanlang / Выберите язык:</b>",
    "lang_changed": "✅ Language changed: <b>🇬🇧 English</b>",
    "lang_name": "🇬🇧 English",

    "welcome": (
        "🔥 Hello! Welcome to @hofizbot. "
        "You can download the following via this bot:\n\n"
        "• Instagram — posts and IGTV with audio;\n"
        "• TikTok — watermark-free video + audio;\n"
        "• Snapchat — watermark-free video + audio;\n"
        "• Likee — watermark-free video + audio;\n"
        "• Pinterest — watermark-free videos and images + audio;\n\n"
        "Shazam features:\n"
        "• Song or artist name\n"
        "• Song lyrics\n"
        "• Voice message\n"
        "• Video\n"
        "• Audio\n"
        "• Video note\n\n"
        "🚀 Send a link to download a video!\n"
        "😎 The bot also works in groups!"
    ),
    "help": (
        "📖 <b>Help</b>\n\n"
        "<b>📥 Download video:</b>\n"
        "Send a link → Tap \"🎬 Video\" → Choose quality\n\n"
        "<b>🎵 Download music:</b>\n"
        "Send a link → Tap \"🎵 Music\"\n\n"
        "<b>🔍 Search music:</b>\n"
        "Type the song name or artist\n\n"
        "<b>🎵 Inline mode:</b>\n"
        "<code>@hofizbot song name</code>\n\n"
        "<b>🔍 Shazam:</b>\n"
        "Send audio, voice, video or video note\n\n"
        "<b>⚙️ Commands:</b>\n"
        "/start — Main menu\n"
        "/lang — Change language\n"
        "/help — Help\n"
        "/myid — Your ID"
    ),

    "btn_add_to_group": "➕ Add to group",
    "btn_inline_search": "💬 Inline search",
    "btn_change_lang": "🌐 Change language",

    "err_no_url": (
        "❌ No link found in your message.\n\n"
        "📎 Send a YouTube, Instagram, TikTok, Facebook or Twitter link."
    ),
    "err_unsupported": (
        "❌ This platform is not supported.\n\n"
        "✅ Supported platforms:\n"
        "• YouTube\n• Instagram\n• TikTok\n• Facebook\n• Twitter/X\n"
        "• Pinterest\n• Likee\n• Snapchat\n• Reddit\n• Spotify"
    ),
    "err_rate_limit": "⏱ Too many requests. Please wait a moment.",
    "err_too_many_active": "⚠️ You are already downloading {count} file(s). Please wait.",
    "err_ig_blocked": (
        "⏱ Instagram temporarily blocked requests (rate-limit).\n"
        "• Try again in 1-2 minutes\n"
        "• Or send a link from another platform"
    ),
    "err_login_required": "🔒 This content requires login or is private.",
    "err_not_available": "❌ Content not available or deleted.",
    "err_private": "🔒 Private content.",
    "err_geo": "🌍 Not available in your region.",
    "err_file_too_large": "❌ File too large ({size})!\n\nMax: {max_size}",
    "err_retry_or_other": "🔁 Try again or send another link.",
    "err_generic": "❌ Unexpected error: {error}",
    "err_banned": "🚫 You are banned.",

    "dl_detected": "✅ <b>{platform}</b> link detected!\n\nChoose download type:",
    "dl_in_progress": "⏳ <b>Downloading...</b>\n\n⚡ 16 parallel connections\n📊 0%",
    "dl_progress": "📥 <b>Downloading:</b> {progress}%\n{bar}\n📦 {downloaded} / {total}",
    "dl_compressing": "🗜 <b>File is large ({size}), compressing...</b>\n\n⏱ Downloaded in: {time}s\n📦 Compressing via ffmpeg...",
    "dl_converting": "🔄 <b>Video adapted to format</b>",
    "dl_uploading": "📤 <b>Sending to Telegram...</b>\n\n📁 {size} | ⏱ Downloaded in {time}s",
    "dl_cached": "⚡ <b>Sending from cache...</b> (0 seconds!)",
    "dl_cancelled": "❌ Cancelled.",
    "dl_success_video": "🎬 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}s",
    "dl_success_audio": "🎵 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}s",
    "dl_cached_video": "🎬 {title}\n⚡ From cache",
    "dl_cached_audio": "🎵 {title}\n⚡ From cache",

    "fmt_choose": "Choose download type:",
    "fmt_video": "🎬 Video",
    "fmt_audio": "🎵 Music (MP3)",
    "fmt_cancel": "❌ Cancel",
    "quality_choose": "📺 Choose video quality:",
    "quality_back": "⬅️ Back",

    "shazam_analyzing": "🎵 <b>Recognizing music...</b>\n\n🔍 Searching via Shazam...",
    "shazam_found": "🎵 <b>Song from video identified:</b>\n🎤 <b>{artist}</b>\n🎶 <i>{title}</i>",
    "shazam_not_found": "❌ <b>Song not recognized</b>\n\n{reason}",
    "shazam_album": "💿 Album: {album}",
    "shazam_year": "📅 Year: {year}",
    "shazam_genre": "🏷 Genre: {genre}",
    "shazam_btn_download_song": "⬇️ Download song",
    "shazam_btn_download_music": "🎵 Download music",
    "shazam_btn_shazam": "🔗 Shazam",
    "shazam_downloading": "🎵 <b>Downloading...</b>\n\n🔍 <b>{artist} — {title}</b>\n📥 Searching on YouTube...",
    "shazam_download_failed": "❌ <b>Song not found</b>\n\nCould not find \"{query}\" on YouTube.",
    "shazam_stale": "❌ Data expired. Send the audio again.",

    "cached_from_cache": "⚡ From cache",
    "video_uploading_in_progress": "Uploading...",

    "stats_title": "📊 <b>Bot Statistics</b>",
    "stats_cache_status": "📦 Cache: {status}",
    "stats_cached_items": "🗂 Cached files: {count}",
    "stats_memory": "💾 Memory: {memory}",
    "stats_no_cache": "📊 <b>Bot Statistics</b>\n\nCache not connected.",

    "myid_text": "🆔 Your Telegram ID: <code>{id}</code>",

    "search_prompt": "🔍 Searching: <b>{query}</b>",
    "search_no_results": "❌ Nothing found.",
    "search_results_title": "🔍 <b>Results:</b> {query}",
}
