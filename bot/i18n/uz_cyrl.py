"""Ўзбек (кирилл)."""

LANG = {
    # ===== Language selector =====
    "lang_choose": "🌐 <b>Tilni tanlang / Тилни танланг / Выберите язык / Choose language:</b>",
    "lang_changed": "✅ Тил ўзгартирилди: <b>🇺🇿 Ўзбек (кирилл)</b>",
    "lang_name": "🇺🇿 Ўзбек",

    # ===== Start / Help =====
    "welcome": (
        "🔥 Ассалому алайкум. @hofizbot га Хуш келибсиз. "
        "Бот орқали қуйидагиларни юклаб олишингиз мумкин:\n\n"
        "• Instagram — пост ва IGTV + аудио билан;\n"
        "• TikTok — сув белгисиз видео + аудио билан;\n"
        "• Snapchat — сув белгисиз видео + аудио билан;\n"
        "• Likee — сув белгисиз видео + аудио билан;\n"
        "• Pinterest — сув белгисиз видео ва расмлар + аудио билан;\n\n"
        "Shazam функцияси:\n"
        "• Қўшиқ номи ёки ижрочи исми\n"
        "• Қўшиқ матни\n"
        "• Овозли хабар\n"
        "• Видео\n"
        "• Аудио\n"
        "• Видео хабар\n\n"
        "🚀 Юклаб олмоқчи бўлган видеога ҳаволани юборинг!\n"
        "😎 Бот гуруҳларда ҳам ишлай олади!"
    ),
    "help": (
        "📖 <b>Ёрдам</b>\n\n"
        "<b>📥 Видео юклаш:</b>\n"
        "Ҳаволани юборинг → \"🎬 Видео\" тугмасини босинг → Сифат танланг\n\n"
        "<b>🎵 Мусиқа юклаш:</b>\n"
        "Ҳаволани юборинг → \"🎵 Мусиқа\" тугмасини босинг\n\n"
        "<b>🔍 Мусиқа қидириш:</b>\n"
        "Қўшиқ номи ёки санъаткор исмини ёзинг\n\n"
        "<b>🎵 Inline режим:</b>\n"
        "<code>@hofizbot қўшиқ номи</code>\n\n"
        "<b>🔍 Shazam:</b>\n"
        "Аудио, voice, видео ёки видео note юборинг\n\n"
        "<b>⚙️ Буйруқлар:</b>\n"
        "/start — Бош меню\n"
        "/lang — Тилни ўзгартириш\n"
        "/help — Ёрдам\n"
        "/myid — ID рақамингиз"
    ),

    "btn_add_to_group": "➕ Гуруҳга қўшиш",
    "btn_inline_search": "💬 Inline қидирув",
    "btn_change_lang": "🌐 Тилни ўзгартириш",

    "err_no_url": (
        "❌ Хабарингизда ҳавола топилмади.\n\n"
        "📎 YouTube, Instagram, TikTok, Facebook ёки Twitter ҳаволасини юборинг."
    ),
    "err_unsupported": (
        "❌ Бу платформа қўлланилмайди.\n\n"
        "✅ Қўлланадиган платформалар:\n"
        "• YouTube\n• Instagram\n• TikTok\n• Facebook\n• Twitter/X\n"
        "• Pinterest\n• Likee\n• Snapchat\n• Reddit\n• Spotify"
    ),
    "err_rate_limit": "⏱ Жуда кўп сўров юбордингиз. Бироз кутинг.",
    "err_too_many_active": "⚠️ Сиз аллақачон {count} та файл юкламоқдасиз. Кутинг.",
    "err_ig_blocked": (
        "⏱ Instagram вақтинча блоклаб қўйди (rate-limit).\n"
        "• 1-2 дақиқадан сўнг қайта уриниб кўринг\n"
        "• Ёки бошқа платформа ҳаволасини юборинг"
    ),
    "err_login_required": "🔒 Бу контент логин талаб қилади ёки шахсий.",
    "err_not_available": "❌ Контент мавжуд эмас ёки ўчирилган.",
    "err_private": "🔒 Шахсий контент.",
    "err_geo": "🌍 Сизнинг ҳудудингизда мавжуд эмас.",
    "err_file_too_large": "❌ Файл жуда катта ({size})!\n\nМаксимал: {max_size}",
    "err_retry_or_other": "🔁 Қайтадан уриниб кўринг ёки бошқа ҳавола юборинг.",
    "err_generic": "❌ Кутилмаган хато: {error}",
    "err_banned": "🚫 Сиз бан қилингансиз.",

    "dl_detected": "✅ <b>{platform}</b> ҳаволаси аниқланди!\n\nЮклаб олиш турини танланг:",
    "dl_in_progress": "⏳ <b>Юклаб олинмоқда...</b>\n\n⚡ 16 та параллел уланиш\n📊 0%",
    "dl_progress": "📥 <b>Юкланмоқда:</b> {progress}%\n{bar}\n📦 {downloaded} / {total}",
    "dl_compressing": "🗜 <b>Файл катта ({size}), сиқилмоқда...</b>\n\n⏱ Юклаб олиш: {time}с\n📦 ffmpeg билан сиқилмоқда...",
    "dl_converting": "🔄 <b>Видео форматга мослаштирилди</b>",
    "dl_uploading": "📤 <b>Telegram'га юборилмоқда...</b>\n\n📁 {size} | ⏱ {time}с да юкланди",
    "dl_cached": "⚡ <b>Cache-дан юборилмоқда...</b> (0 сония!)",
    "dl_cancelled": "❌ Бекор қилинди.",
    "dl_success_video": "🎬 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}с",
    "dl_success_audio": "🎵 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}с",
    "dl_cached_video": "🎬 {title}\n⚡ Cache-дан юборилди",
    "dl_cached_audio": "🎵 {title}\n⚡ Cache-дан юборилди",

    "fmt_choose": "Юклаб олиш турини танланг:",
    "fmt_video": "🎬 Видео",
    "fmt_audio": "🎵 Мусиқа (MP3)",
    "fmt_cancel": "❌ Бекор қилиш",
    "quality_choose": "📺 Видео сифатини танланг:",
    "quality_back": "⬅️ Орқага",

    "shazam_analyzing": "🎵 <b>Мусиқа аниқланмоқда...</b>\n\n🔍 Shazam орқали қидирилмоқда...",
    "shazam_found": "🎵 <b>Видеодаги қўшиқ аниқланди:</b>\n🎤 <b>{artist}</b>\n🎶 <i>{title}</i>",
    "shazam_not_found": "❌ <b>Қўшиқ аниқланмади</b>\n\n{reason}",
    "shazam_album": "💿 Альбом: {album}",
    "shazam_year": "📅 Йил: {year}",
    "shazam_genre": "🏷 Жанр: {genre}",
    "shazam_btn_download_song": "⬇️ Қўшиқни юклаб олиш",
    "shazam_btn_download_music": "🎵 Мусиқани юклаб олиш",
    "shazam_btn_shazam": "🔗 Shazam",
    "shazam_downloading": "🎵 <b>Юклаб олинмоқда...</b>\n\n🔍 <b>{artist} — {title}</b>\n📥 YouTube'дан қидирилмоқда...",
    "shazam_download_failed": "❌ <b>Қўшиқ топилмади</b>\n\nYouTube'дан \"{query}\" топилмади.",
    "shazam_stale": "❌ Маълумот эскирган. Қайтадан аудио юборинг.",

    "cached_from_cache": "⚡ Cache-дан юборилди",
    "video_uploading_in_progress": "Юкланмоқда...",

    "stats_title": "📊 <b>Бот Статистикаси</b>",
    "stats_cache_status": "📦 Cache: {status}",
    "stats_cached_items": "🗂 Сақланган файллар: {count}",
    "stats_memory": "💾 Хотира: {memory}",
    "stats_no_cache": "📊 <b>Бот Статистикаси</b>\n\nCache уланмаган.",

    "myid_text": "🆔 Сизнинг Telegram ID: <code>{id}</code>",

    "search_prompt": "🔍 Қидирилмоқда: <b>{query}</b>",
    "search_no_results": "❌ Ҳеч нарса топилмади.",
    "search_results_title": "🔍 <b>Натижалар:</b> {query}",
}
