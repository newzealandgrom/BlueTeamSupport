import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TimedOut, NetworkError, RetryAfter

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы
TOKEN = "TOKEN"  # Токен бота
ADMIN_ID = ADMIN ID  # ID администратора
ADMIN_IDS = {ADMIN ID}  # Множество ID администраторов

# Настройки для работы с сетью
# Определяем параметры запросов для стабильной работы
REQUEST_KWARGS = {
    "read_timeout": 30,
    "connect_timeout": 30,
    "write_timeout": 30,
    "pool_timeout": 30,
}

# Настройки прокси (раскомментируйте и настройте, если доступ к Telegram API ограничен)
# PROXY_URL = 'socks5://user:password@proxy_address:port'

# Хранилище истории переписки с пользователями
# В реальном проекте лучше использовать базу данных
user_messages = {}  # Формат: {user_id: [{"type": "text|media", "content": str, "media_type": str, "file_id": str, "sender": "user|admin"}]}
user_info = {}  # Формат: {user_id: {"first_name": str, "last_name": str, "username": str}}
user_states = {}  # Формат: {user_id: {"action": str, "step": str}}


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    user = update.effective_user
    user_id = user.id

    # Инициализация истории сообщений для нового пользователя
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    # Сохраняем информацию о пользователе
    user_info[user_id] = {
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "username": user.username or ""
    }

    # Приветственное сообщение с клавиатурой для админов
    if user_id in ADMIN_IDS:
        # Клавиатура для админов
        keyboard = [
            [KeyboardButton("🛠 Панель админа"), KeyboardButton("📝 Список пользователей")],
            [KeyboardButton("📊 Статистика"), KeyboardButton("ℹ️ Помощь")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"🚀 Добро пожаловать, {user.first_name}!\n\n"
            "🛠 Вы администратор бота.\n"
            "Используйте кнопки ниже для управления.",
            reply_markup=reply_markup
        )
    else:
        # Клавиатура для обычных пользователей
        keyboard = [
            [KeyboardButton("ℹ️ Помощь"), KeyboardButton("📞 Связаться с поддержкой")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Здравствуйте, {user.first_name}! Я бот для связи с администратором.\n\n"
            "💬 Отправьте любое сообщение (текст, фото, видео, голосовое), и администратор ответит вам.",
            reply_markup=reply_markup
        )

    # Уведомление всех администраторов о новом пользователе
    if user_id not in ADMIN_IDS:
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                text=f"Новый пользователь начал общение:\n"
                f"Имя: {user.first_name} {user.last_name or ''}\n"
                f"Username: @{user.username or 'отсутствует'}\n"
                f"ID: {user_id}",
            )
            except (TimedOut, NetworkError) as e:
                logger.error(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
                # Повторная попытка отправки
                await asyncio.sleep(1)
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"Новый пользователь начал общение:\n"
                        f"Имя: {user.first_name} {user.last_name or ''}\n"
                        f"Username: @{user.username or 'отсутствует'}\n"
                        f"ID: {user_id}",
                    )
                except Exception as e2:
                    logger.error(f"Повторная ошибка при отправке уведомления админу {admin_id}: {e2}")


# Безопасная отправка сообщений с авто-повтором при ошибках
async def safe_send_message(context, chat_id, text, reply_markup=None, max_retries=3):
    """Отправляет сообщение с повторными попытками при возникновении ошибок сети."""
    for attempt in range(max_retries):
        try:
            return await context.bot.send_message(
                chat_id=chat_id, text=text, reply_markup=reply_markup
            )
        except RetryAfter as e:
            # Если сервер просит подождать, ждем указанное время
            logger.info(f"Превышен лимит запросов. Ожидание {e.retry_after} секунд")
            await asyncio.sleep(e.retry_after)
        except (TimedOut, NetworkError) as e:
            # При ошибках сети ждем и пробуем снова
            wait_time = (
                attempt + 1
            ) * 2  # Увеличиваем время ожидания с каждой попыткой
            logger.warning(
                f"Ошибка сети: {e}. Повторная попытка через {wait_time} сек."
            )
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при отправке сообщения: {e}")
            if attempt == max_retries - 1:
                # Если это последняя попытка, пробрасываем ошибку выше
                raise
            await asyncio.sleep(2)

    # Если все попытки не удались
    logger.error(f"Не удалось отправить сообщение после {max_retries} попыток")
    return None


# Обработчик всех сообщений (текст, фото, видео, голос)
async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает все типы сообщений."""
    user = update.effective_user
    user_id = user.id
    message = update.message
    
    # Проверяем, является ли это нажатием кнопки клавиатуры для обычных пользователей
    if message.text and user_id not in ADMIN_IDS:
        if message.text in ["ℹ️ Помощь", "📞 Связаться с поддержкой"]:
            await handle_keyboard_buttons(update, context)
            return
    
    # Определяем тип сообщения
    if message.text:
        message_text = message.text
        message_type = "💬 Текст"
    elif message.photo:
        message_text = message.caption or "[Фото без подписи]"
        message_type = "🖼 Фото"
    elif message.video:
        message_text = message.caption or "[Видео без подписи]"
        message_type = "🎥 Видео"
    elif message.voice:
        message_text = "[Голосовое сообщение]"
        message_type = "🎙 Голос"
    elif message.document:
        message_text = message.caption or f"[Документ: {message.document.file_name or 'без имени'}]"
        message_type = "📄 Документ"
    elif message.audio:
        message_text = message.caption or "[Аудио файл]"
        message_type = "🎵 Аудио"
    elif message.sticker:
        message_text = f"[Стикер: {message.sticker.emoji or '😀'}]"
        message_type = "🎆 Стикер"
    else:
        message_text = "[Неподдерживаемый тип сообщения]"
        message_type = "❓ Неизвестно"

    # Инициализация истории сообщений и информации о пользователе
    if user_id not in user_messages:
        user_messages[user_id] = []
    
    if user_id not in user_info:
        user_info[user_id] = {
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "username": user.username or ""
        }

    # Добавление сообщения в историю
    message_data = {
        "type": "text" if message.text else "media",
        "content": message_text,
        "media_type": message_type,
        "file_id": None,
        "sender": "admin" if user_id in ADMIN_IDS else "user"
    }
    
    # Сохраняем file_id для медиафайлов
    if message.photo:
        message_data["file_id"] = message.photo[-1].file_id
    elif message.video:
        message_data["file_id"] = message.video.file_id
    elif message.voice:
        message_data["file_id"] = message.voice.file_id
    elif message.document:
        message_data["file_id"] = message.document.file_id
    elif message.audio:
        message_data["file_id"] = message.audio.file_id
    elif message.sticker:
        message_data["file_id"] = message.sticker.file_id
    
    user_messages[user_id].append(message_data)

    # Если сообщение от пользователя (не от админа)
    if user_id not in ADMIN_IDS:
        # Создаем кнопку для ответа
        keyboard = [
            [InlineKeyboardButton("Ответить", callback_data=f"reply_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение всем администраторам
        try:
            for admin_id in ADMIN_IDS:
                # Сначала отправляем информационное сообщение
                await safe_send_message(
                    context=context,
                    chat_id=admin_id,
                    text=f"{message_type} от пользователя:\n"
                    f"Имя: {user.first_name} {user.last_name or ''}\n"
                    f"Username: @{user.username or 'отсутствует'}\n"
                    f"ID: {user_id}\n\n"
                    f"Сообщение: {message_text}",
                    reply_markup=reply_markup,
                )
                
                # Затем пересылаем медиафайл, если он есть
                if message.photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=message.photo[-1].file_id,  # Берем фото наивысшего качества
                        caption=f"📸 Фото от пользователя {user_id}"
                    )
                elif message.video:
                    await context.bot.send_video(
                        chat_id=admin_id,
                        video=message.video.file_id,
                        caption=f"🎥 Видео от пользователя {user_id}"
                    )
                elif message.voice:
                    await context.bot.send_voice(
                        chat_id=admin_id,
                        voice=message.voice.file_id,
                        caption=f"🎙 Голосовое от пользователя {user_id}"
                    )
                elif message.document:
                    await context.bot.send_document(
                        chat_id=admin_id,
                        document=message.document.file_id,
                        caption=f"📄 Документ от пользователя {user_id}"
                    )
                elif message.audio:
                    await context.bot.send_audio(
                        chat_id=admin_id,
                        audio=message.audio.file_id,
                        caption=f"🎵 Аудио от пользователя {user_id}"
                    )
                elif message.sticker:
                    await context.bot.send_sticker(
                        chat_id=admin_id,
                        sticker=message.sticker.file_id
                    )

            # Отправляем подтверждение пользователю
            await update.message.reply_text(
                "Ваше сообщение отправлено администратору. Ожидайте ответа."
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения: {e}")
            await update.message.reply_text(
                "Произошла ошибка при отправке вашего сообщения. Пожалуйста, попробуйте позже."
            )
    # Если сообщение от админа и оно не является ответом
    elif user_id in ADMIN_IDS and not context.user_data.get("replying_to"):
        await update.message.reply_text(
            "Чтобы ответить пользователю, используйте кнопку 'Ответить' под его сообщением."
        )


# Обработчик кнопок (объединенные меню и ответы)
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок."""
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    
    await query.answer()
    
    # Меню админа
    if data.startswith("menu_") or data == "back_to_menu":
        if user_id not in ADMIN_IDS:
            await query.answer("У вас нет прав для этого действия.")
            return
            
        if data == "menu_close":
            await query.delete_message()
        elif data == "menu_list_users":
            await show_users_list(query, context)
        elif data == "menu_add_admin":
            await start_add_admin_process(query, context)
        elif data == "menu_remove_admin":
            await start_remove_admin_process(query, context)
        elif data == "menu_stats":
            await show_statistics(query, context)
        elif data == "back_to_menu":
            await show_main_menu(query, context)
        return
    
    # Ответы на сообщения
    if data.startswith("reply_"):
        if user_id not in ADMIN_IDS:
            await query.answer("У вас нет прав для этого действия.")
            return
            
        user_reply_id = int(data.split("_")[1])
        context.user_data["replying_to"] = user_reply_id
        
        # Отправляем текстовую информацию
        try:
            await query.edit_message_text(
                text=f"Вы отвечаете пользователю с ID {user_reply_id}.\n\n"
                f"📝 История переписки будет показана ниже.\n\n"
                f"Напишите ваш ответ (или /cancel для отмены):"
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {e}")
            await safe_send_message(
                context=context,
                chat_id=user_id,
                text=f"Вы отвечаете пользователю с ID {user_reply_id}.\n\n"
                f"📝 История переписки будет показана ниже.\n\n"
                f"Напишите ваш ответ (или /cancel для отмены):",
            )
        
        # Отправляем историю с медиафайлами
        await send_history_with_media(context, user_id, user_reply_id)


# Функция для отправки истории с медиафайлами
async def send_history_with_media(context, admin_id, user_reply_id):
    """Отправляет историю переписки с медиафайлами администратору."""
    history = user_messages.get(user_reply_id, [])
    
    if not history:
        await safe_send_message(
            context=context,
            chat_id=admin_id,
            text="📝 История переписки пуста."
        )
        return
    
    await safe_send_message(
        context=context,
        chat_id=admin_id,
        text="📝 История переписки:"
    )
    
    for msg in history:
        sender_label = "👤 Пользователь" if msg["sender"] == "user" else "👨‍💼 Администратор"
        
        if msg["type"] == "text":
            # Текстовое сообщение
            await safe_send_message(
                context=context,
                chat_id=admin_id,
                text=f"{sender_label}: {msg['content']}"
            )
        else:
            # Медиафайл
            caption = f"{sender_label} ({msg['media_type']})"
            if msg['content'] and msg['content'] not in ["[Фото без подписи]", "[Видео без подписи]", "[Голосовое сообщение]", "[Аудио файл]"]:
                caption += f": {msg['content']}"
            
            try:
                if msg["media_type"] == "🖼 Фото":
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=msg["file_id"],
                        caption=caption
                    )
                elif msg["media_type"] == "🎥 Видео":
                    await context.bot.send_video(
                        chat_id=admin_id,
                        video=msg["file_id"],
                        caption=caption
                    )
                elif msg["media_type"] == "🎙 Голос":
                    await context.bot.send_voice(
                        chat_id=admin_id,
                        voice=msg["file_id"],
                        caption=caption
                    )
                elif msg["media_type"] == "📄 Документ":
                    await context.bot.send_document(
                        chat_id=admin_id,
                        document=msg["file_id"],
                        caption=caption
                    )
                elif msg["media_type"] == "🎵 Аудио":
                    await context.bot.send_audio(
                        chat_id=admin_id,
                        audio=msg["file_id"],
                        caption=caption
                    )
                elif msg["media_type"] == "🎆 Стикер":
                    await context.bot.send_sticker(
                        chat_id=admin_id,
                        sticker=msg["file_id"]
                    )
                    if caption:
                        await safe_send_message(
                            context=context,
                            chat_id=admin_id,
                            text=caption
                        )
            except Exception as e:
                logger.error(f"Ошибка при отправке медиафайла в историю: {e}")
                await safe_send_message(
                    context=context,
                    chat_id=admin_id,
                    text=f"{sender_label} ({msg['media_type']}): [Ошибка загрузки медиафайла]"
                )


# Обработчик ответа администратора
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ответ администратора на сообщение пользователя."""
    user_id = update.effective_user.id

    # Проверяем, что это администратор и что он отвечает кому-то
    logger.info(f"admin_reply called for user {user_id}, replying_to: {context.user_data.get('replying_to')}")
    if user_id in ADMIN_IDS and context.user_data.get("replying_to"):
        reply_to_id = context.user_data["replying_to"]
        message_text = update.message.text

        # Если админ хочет отменить ответ
        if message_text == "/cancel":
            del context.user_data["replying_to"]
            await update.message.reply_text("Ответ отменен.")
            return

        # Добавляем ответ в историю переписки
        if reply_to_id in user_messages:
            admin_reply_data = {
                "type": "text",
                "content": message_text,
                "media_type": "💬 Текст",
                "file_id": None,
                "sender": "admin"
            }
            user_messages[reply_to_id].append(admin_reply_data)

        # Отправляем ответ пользователю
        try:
            await safe_send_message(
                context=context,
                chat_id=reply_to_id,
                text=f"Ответ администратора: {message_text}",
            )
            # Подтверждаем отправку
            await update.message.reply_text(
                f"Ваш ответ был отправлен пользователю с ID {reply_to_id}."
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке ответа: {e}")
            await update.message.reply_text(
                f"Не удалось отправить ответ пользователю. Ошибка: {e}"
            )

        # Сбрасываем состояние ответа
        del context.user_data["replying_to"]


# Обработчик кнопок клавиатуры
async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия кнопок клавиатуры."""
    user_id = update.effective_user.id
    button_text = update.message.text
    
    # Обработка кнопок для обычных пользователей
    if user_id not in ADMIN_IDS:
        if button_text == "ℹ️ Помощь":
            await help_command(update, context)
        elif button_text == "📞 Связаться с поддержкой":
            await update.message.reply_text(
                "💬 Вы уже находитесь в чате поддержки!\n\n"
                "Просто отправьте ваше сообщение (текст, фото, видео, голосовое), "
                "и администратор обязательно ответит вам."
            )
        return
    
    # Обработка кнопок для админов
    if button_text == "🛠 Панель админа":
        await admin_menu(update, context)
    elif button_text == "📝 Список пользователей":
        await list_users(update, context)
    elif button_text == "📊 Статистика":
        await show_bot_statistics(update, context)
    elif button_text == "ℹ️ Помощь":
        await help_command(update, context)


# Показ статистики бота через кнопку
async def show_bot_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику бота."""
    admin_count = len(ADMIN_IDS)
    total_users = len(user_messages)
    total_messages = sum(len(messages) for messages in user_messages.values())
    
    text = f"📊 <b>Статистика бота</b>\n\n"
    text += f"🔑 Администраторов: {admin_count}\n"
    text += f"💬 Пользователей: {total_users}\n"
    text += f"📝 Всего сообщений: {total_messages}\n\n"
    text += f"🌍 Доступ: Открыт для всех"
    
    await update.message.reply_text(text, parse_mode='HTML')


# Обработчик команды /list для отображения списка всех пользователей
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает список всех пользователей, которые писали боту."""
    user_id = update.effective_user.id

    # Проверяем, что это администратор
    if user_id in ADMIN_IDS:
        if not user_messages:
            await update.message.reply_text("Пока нет сообщений от пользователей.")
            return

        # Создаем список пользователей с кнопками для просмотра истории
        keyboard = []
        for uid in user_messages:
            if uid != ADMIN_ID:
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            f"Пользователь ID: {uid}", callback_data=f"reply_{uid}"
                        )
                    ]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await safe_send_message(
                context=context,
                chat_id=user_id,
                text="Выберите пользователя, чтобы просмотреть историю и ответить:",
                reply_markup=reply_markup,
            )
        except Exception as e:
            logger.error(f"Ошибка при отображении списка пользователей: {e}")
            await update.message.reply_text(
                "Ошибка при получении списка пользователей. Пожалуйста, попробуйте позже."
            )
    else:
        await update.message.reply_text("Эта команда доступна только администратору.")


# Обработчик команды /admin_menu - главное меню админа
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает главное меню администратора."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return
    
    keyboard = [
        [InlineKeyboardButton("📝 Список пользователей", callback_data="menu_list_users")],
        [InlineKeyboardButton("🔑 Добавить админа", callback_data="menu_add_admin"),
         InlineKeyboardButton("🚫 Удалить админа", callback_data="menu_remove_admin")],
        [InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton("❌ Закрыть меню", callback_data="menu_close")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🛠 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )








# Обработчик команды /add_admin
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Добавляет нового администратора."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите ID пользователя.\nПример: /add_admin 123456789")
        return
    
    try:
        target_user_id = int(context.args[0])
        
        if target_user_id in ADMIN_IDS:
            await update.message.reply_text("Пользователь уже является администратором.")
            return
            
        ADMIN_IDS.add(target_user_id)
        
        await update.message.reply_text(f"Пользователь {target_user_id} добавлен в список администраторов.")
        
    except ValueError:
        await update.message.reply_text("Некорректный формат. Укажите числовой ID.")


# Обработчик команды /remove_admin
async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаляет администратора."""
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return
    
    if not context.args:
        await update.message.reply_text("Укажите ID администратора.\nПример: /remove_admin 123456789")
        return
    
    try:
        target_user_id = int(context.args[0])
        
        if target_user_id == user_id:
            await update.message.reply_text("Нельзя удалить самого себя из администраторов.")
            return
            
        if target_user_id == ADMIN_ID:
            await update.message.reply_text("Нельзя удалить основного администратора.")
            return
            
        if target_user_id in ADMIN_IDS:
            ADMIN_IDS.remove(target_user_id)
            await update.message.reply_text(f"Пользователь {target_user_id} удален из списка администраторов.")
        else:
            await update.message.reply_text(f"Пользователь {target_user_id} не является администратором.")
        
    except ValueError:
        await update.message.reply_text("Некорректный формат. Укажите числовой ID.")


# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает справочную информацию."""
    user_id = update.effective_user.id

    if user_id in ADMIN_IDS:
        await update.message.reply_text(
            "🛠 Команды администратора:\n\n"
            "🚀 /admin_menu - Панель управления\n"
            "/start - Начать работу\n"
            "/list - Список пользователей\n"
            "/help - Показать справку\n\n"
            "🔥 Используйте кнопки клавиатуры для быстрого доступа!"
        )
    else:
        await update.message.reply_text(
            "💬 Отправьте любое сообщение (текст, фото, видео, голосовое), и администратор ответит вам."
        )


# Обработчик сообщений для ввода ID в меню
async def handle_menu_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ввод ID пользователя в рамках меню."""
    user_id = update.effective_user.id
    
    # Проверяем, что это админ и он в состоянии ожидания ввода ID
    if user_id not in ADMIN_IDS:
        return
    
    # Проверка кнопок клавиатуры (приоритет выше состояний ожидания)
    if update.message.text in ["🛠 Панель админа", "📝 Список пользователей", "📊 Статистика", "ℹ️ Помощь"]:
        # Если пользователь был в состоянии ожидания, сбрасываем его
        if user_id in user_states:
            del user_states[user_id]
        await handle_keyboard_buttons(update, context)
        return
    
    # Если админ не в состоянии ожидания, проверяем админские ответы
    if user_id not in user_states:
        # Если это не кнопка клавиатуры, проверяем - может админ отвечает пользователю
        if context.user_data.get("replying_to"):
            await admin_reply(update, context)
            return
        
        # Если ни то ни другое, возвращаемся - пусть обрабатывает handle_all_messages
        return
    
    # Проверяем состояние ожидания
    state = user_states[user_id]
    if state.get("step") != "waiting_for_id":
        return
    
    # Обрабатываем специальные команды
    if update.message.text == "/cancel":
        del user_states[user_id]
        await update.message.reply_text("❌ Операция отменена.")
        return
    
    # Пытаемся парсить ID
    try:
        target_id = int(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Некорректный формат. Укажите числовой ID или нажмите /cancel для отмены.")
        return
    
    action = state.get("action")
    del user_states[user_id]
    
    if action == "add_admin":
        await process_add_admin_menu(update, target_id)
    elif action == "remove_admin":
        await process_remove_admin_menu(update, target_id, user_id)


async def process_add_admin_menu(update: Update, target_id: int) -> None:
    if target_id in ADMIN_IDS:
        await update.message.reply_text("ℹ️ Уже админ.")
        return
    ADMIN_IDS.add(target_id)
    await update.message.reply_text(f"✅ {target_id} назначен админом.")


async def process_remove_admin_menu(update: Update, target_id: int, current_user_id: int) -> None:
    if target_id == current_user_id:
        await update.message.reply_text("❌ Нельзя удалить себя.")
        return
    if target_id == ADMIN_ID:
        await update.message.reply_text("❌ Нельзя удалить основного админа.")
        return
    if target_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Не админ.")
        return
    ADMIN_IDS.remove(target_id)
    await update.message.reply_text(f"✅ {target_id} удален из админов.")


# Меню процессы
async def start_add_admin_process(query, context) -> None:
    user_id = query.from_user.id
    user_states[user_id] = {"action": "add_admin", "step": "waiting_for_id"}
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
    await query.edit_message_text(
        "🔑 <b>Добавление админа</b>\n\nВведите ID пользователя:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
    )

async def start_remove_admin_process(query, context) -> None:
    user_id = query.from_user.id
    removable = [aid for aid in ADMIN_IDS if aid != ADMIN_ID and aid != user_id]
    
    if not removable:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
        await query.edit_message_text(
            "🚫 <b>Удаление админа</b>\n\nНет админов для удаления.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
        )
        return
    
    user_states[user_id] = {"action": "remove_admin", "step": "waiting_for_id"}
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")]]
    
    text = "🚫 <b>Удаление админа</b>\n\nВведите ID:\n\n📋 <b>Доступные:</b>\n"
    for aid in removable:
        text += f"  • ID: {aid}\n"
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_users_list(query, context) -> None:
    admin_count = len(ADMIN_IDS)
    total_users = len(user_messages)
    
    text = f"📊 <b>Список пользователей</b>\n\n"
    text += f"🔑 Админов: {admin_count}\n💬 Общались: {total_users}\n\n"
    
    if ADMIN_IDS:
        text += "🔑 <b>Админы:</b>\n"
        for aid in ADMIN_IDS:
            if aid in user_info:
                info = user_info[aid]
                name = f"{info['first_name']} {info['last_name']}".strip()
                username = f"@{info['username']}" if info['username'] else "нет"
                text += f"  • {name} ({username}) - ID: {aid}\n"
            else:
                text += f"  • ID: {aid}\n"
    
    text += "\nℹ️ Доступ к боту: Открыт для всех"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_statistics(query, context) -> None:
    admin_count = len(ADMIN_IDS)
    total_users = len(user_messages)
    total_messages = sum(len(messages) for messages in user_messages.values())
    
    text = f"📊 <b>Статистика</b>\n\n🔑 Админов: {admin_count}\n💬 Пользователей: {total_users}\n📝 Сообщений: {total_messages}\n\n"
    text += f"🌍 Доступ: Открыт для всех"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_main_menu(query, context) -> None:
    keyboard = [
        [InlineKeyboardButton("📝 Список пользователей", callback_data="menu_list_users")],
        [InlineKeyboardButton("🔑 Добавить админа", callback_data="menu_add_admin"),
         InlineKeyboardButton("🚫 Удалить админа", callback_data="menu_remove_admin")],
        [InlineKeyboardButton("📊 Статистика", callback_data="menu_stats")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="menu_close")]
    ]
    
    await query.edit_message_text(
        "🛠 <b>Панель администратора</b>\n\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
    )


# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки, вызванные обновлениями."""
    logger.error(f"Возникла ошибка: {context.error}", exc_info=context.error)

    # Если обновление доступно, отправляем сообщение об ошибке
    if update and hasattr(update, "effective_user") and update.effective_user:
        if update.effective_user.id in ADMIN_IDS:
            error_message = (
                f"Произошла ошибка при обработке обновления: {context.error}"
            )
            try:
                for admin_id in ADMIN_IDS:
                    await safe_send_message(context, admin_id, error_message)
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")


def main() -> None:
    """Основная функция запуска бота."""
    try:
        # Создаем экземпляр приложения с настройками таймаутов
        application_builder = Application.builder().token(TOKEN)

        # Настраиваем HTTP версию и другие параметры
        application_builder = application_builder.get_updates_http_version(
            "1.1"
        ).http_version("1.1")

        # Добавляем прокси, если он настроен
        if "PROXY_URL" in globals() and PROXY_URL:
            application_builder = application_builder.proxy_url(PROXY_URL)
            logger.info(f"Используется прокси: {PROXY_URL}")

        # Создаем приложение
        application = application_builder.build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("list", list_users))
        application.add_handler(CommandHandler("admin_menu", admin_menu))
        application.add_handler(CommandHandler("add_admin", add_admin))
        application.add_handler(CommandHandler("remove_admin", remove_admin))

        # Добавляем обработчик для кнопок
        application.add_handler(CallbackQueryHandler(callback_handler))

        # Обработчик для ввода ID в меню (высокий приоритет)
        # Создаем динамический фильтр админов
        class AdminFilter(filters.MessageFilter):
            def filter(self, message):
                return message.from_user and message.from_user.id in ADMIN_IDS
        
        admin_filter = AdminFilter()
        menu_input_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND & admin_filter, handle_menu_input
        )
        application.add_handler(menu_input_handler)
        
        # Обработчик для ответов админов теперь вызывается из handle_menu_input

        # Общий обработчик всех сообщений (текст, медиа)
        all_message_handler = MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.VOICE | 
             filters.Document.ALL | filters.AUDIO | filters.Sticker.ALL) & ~filters.COMMAND, 
            handle_all_messages
        )
        application.add_handler(all_message_handler)

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        # Запускаем бота с увеличенными таймаутами
        logger.info("Запуск бота...")

        # Используем увеличенный таймаут для соединения
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )

    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        print(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    main()
