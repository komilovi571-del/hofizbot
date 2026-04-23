"""Русский язык."""

LANG = {
    "lang_choose": "🌐 <b>Выберите язык / Tilni tanlang / Choose language:</b>",
    "lang_changed": "✅ Язык изменён: <b>🇷🇺 Русский</b>",
    "lang_name": "🇷🇺 Русский",

    "welcome": (
        "🔥 Здравствуйте! Добро пожаловать в @hofizbot. "
        "С помощью бота вы можете скачать:\n\n"
        "• Instagram — посты и IGTV с аудио;\n"
        "• TikTok — видео без водяного знака + аудио;\n"
        "• Snapchat — видео без водяного знака + аудио;\n"
        "• Likee — видео без водяного знака + аудио;\n"
        "• Pinterest — видео и изображения без водяного знака + аудио;\n\n"
        "Функция Shazam:\n"
        "• Название песни или исполнителя\n"
        "• Текст песни\n"
        "• Голосовое сообщение\n"
        "• Видео\n"
        "• Аудио\n"
        "• Видеосообщение\n\n"
        "🚀 Отправьте ссылку на видео, которое хотите скачать!\n"
        "😎 Бот работает и в группах!"
    ),
    "help": (
        "📖 <b>Помощь</b>\n\n"
        "<b>📥 Скачать видео:</b>\n"
        "Отправьте ссылку → Нажмите \"🎬 Видео\" → Выберите качество\n\n"
        "<b>🎵 Скачать музыку:</b>\n"
        "Отправьте ссылку → Нажмите \"🎵 Музыка\"\n\n"
        "<b>🔍 Поиск музыки:</b>\n"
        "Напишите название песни или исполнителя\n\n"
        "<b>🎵 Inline режим:</b>\n"
        "<code>@hofizbot название песни</code>\n\n"
        "<b>🔍 Shazam:</b>\n"
        "Отправьте аудио, голосовое, видео или кружок\n\n"
        "<b>⚙️ Команды:</b>\n"
        "/start — Главное меню\n"
        "/lang — Сменить язык\n"
        "/help — Помощь\n"
        "/myid — Ваш ID"
    ),

    "btn_add_to_group": "➕ Добавить в группу",
    "btn_inline_search": "💬 Inline поиск",
    "btn_change_lang": "🌐 Сменить язык",

    "err_no_url": (
        "❌ В сообщении нет ссылки.\n\n"
        "📎 Отправьте ссылку на YouTube, Instagram, TikTok, Facebook или Twitter."
    ),
    "err_unsupported": (
        "❌ Эта платформа не поддерживается.\n\n"
        "✅ Поддерживаемые платформы:\n"
        "• YouTube\n• Instagram\n• TikTok\n• Facebook\n• Twitter/X\n"
        "• Pinterest\n• Likee\n• Snapchat\n• Reddit\n• Spotify"
    ),
    "err_rate_limit": "⏱ Слишком много запросов. Подождите немного.",
    "err_too_many_active": "⚠️ Вы уже скачиваете {count} файла(ов). Подождите.",
    "err_ig_blocked": (
        "⏱ Instagram временно заблокировал запросы (rate-limit).\n"
        "• Попробуйте снова через 1-2 минуты\n"
        "• Или отправьте ссылку с другой платформы"
    ),
    "err_login_required": "🔒 Контент требует входа или является приватным.",
    "err_not_available": "❌ Контент недоступен или удалён.",
    "err_private": "🔒 Приватный контент.",
    "err_geo": "🌍 Недоступно в вашем регионе.",
    "err_file_too_large": "❌ Файл слишком большой ({size})!\n\nМаксимум: {max_size}",
    "err_retry_or_other": "🔁 Попробуйте ещё раз или отправьте другую ссылку.",
    "err_generic": "❌ Неожиданная ошибка: {error}",
    "err_banned": "🚫 Вы заблокированы.",

    "dl_detected": "✅ Обнаружена ссылка <b>{platform}</b>!\n\nВыберите тип загрузки:",
    "dl_in_progress": "⏳ <b>Скачивание...</b>\n\n⚡ 16 параллельных соединений\n📊 0%",
    "dl_progress": "📥 <b>Загрузка:</b> {progress}%\n{bar}\n📦 {downloaded} / {total}",
    "dl_compressing": "🗜 <b>Файл большой ({size}), сжимаем...</b>\n\n⏱ Скачано за: {time}с\n📦 Сжатие через ffmpeg...",
    "dl_converting": "🔄 <b>Видео адаптировано под формат</b>",
    "dl_uploading": "📤 <b>Отправка в Telegram...</b>\n\n📁 {size} | ⏱ Скачано за {time}с",
    "dl_cached": "⚡ <b>Отправка из кэша...</b> (0 секунд!)",
    "dl_cancelled": "❌ Отменено.",
    "dl_success_video": "🎬 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}с",
    "dl_success_audio": "🎵 <b>{title}</b>\n⏱ {duration} | 📁 {size} | ⚡ {time}с",
    "dl_cached_video": "🎬 {title}\n⚡ Из кэша",
    "dl_cached_audio": "🎵 {title}\n⚡ Из кэша",

    "fmt_choose": "Выберите тип загрузки:",
    "fmt_video": "🎬 Видео",
    "fmt_audio": "🎵 Музыка (MP3)",
    "fmt_cancel": "❌ Отмена",
    "quality_choose": "📺 Выберите качество видео:",
    "quality_back": "⬅️ Назад",

    "shazam_analyzing": "🎵 <b>Распознавание музыки...</b>\n\n🔍 Поиск через Shazam...",
    "shazam_found": "🎵 <b>Песня из видео найдена:</b>\n🎤 <b>{artist}</b>\n🎶 <i>{title}</i>",
    "shazam_not_found": "❌ <b>Песня не распознана</b>\n\n{reason}",
    "shazam_album": "💿 Альбом: {album}",
    "shazam_year": "📅 Год: {year}",
    "shazam_genre": "🏷 Жанр: {genre}",
    "shazam_btn_download_song": "⬇️ Скачать песню",
    "shazam_btn_download_music": "🎵 Скачать музыку",
    "shazam_btn_shazam": "🔗 Shazam",
    "shazam_downloading": "🎵 <b>Скачивание...</b>\n\n🔍 <b>{artist} — {title}</b>\n📥 Поиск на YouTube...",
    "shazam_download_failed": "❌ <b>Песня не найдена</b>\n\nНа YouTube не найдено \"{query}\".",
    "shazam_stale": "❌ Данные устарели. Отправьте аудио заново.",

    "cached_from_cache": "⚡ Из кэша",
    "video_uploading_in_progress": "Загрузка...",

    "stats_title": "📊 <b>Статистика бота</b>",
    "stats_cache_status": "📦 Кэш: {status}",
    "stats_cached_items": "🗂 Сохранённые файлы: {count}",
    "stats_memory": "💾 Память: {memory}",
    "stats_no_cache": "📊 <b>Статистика бота</b>\n\nКэш не подключён.",

    "myid_text": "🆔 Ваш Telegram ID: <code>{id}</code>",

    "search_prompt": "🔍 Поиск: <b>{query}</b>",
    "search_no_results": "❌ Ничего не найдено.",
    "search_results_title": "🔍 <b>Результаты:</b> {query}",
}
