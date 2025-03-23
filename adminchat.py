import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
TOKEN = "ВАШ ТОКЕН"  # Токен бота
ADMIN_ID = ВАШ ID  # ID администратора

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
user_messages = {}  # Формат: {user_id: [сообщения]}


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    user = update.effective_user
    user_id = user.id

    # Инициализация истории сообщений для нового пользователя
    if user_id not in user_messages:
        user_messages[user_id] = []

    # Приветственное сообщение
    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}! Я бот для связи с администратором. "
        "Напишите ваше сообщение, и администратор ответит вам, как только сможет."
    )

    # Уведомление администратора о новом пользователе
    if user_id != ADMIN_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"Новый пользователь начал общение:\n"
                f"Имя: {user.first_name} {user.last_name or ''}\n"
                f"Username: @{user.username or 'отсутствует'}\n"
                f"ID: {user_id}",
            )
        except (TimedOut, NetworkError) as e:
            logger.error(f"Ошибка при отправке уведомления администратору: {e}")
            # Повторная попытка отправки
            await asyncio.sleep(1)
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"Новый пользователь начал общение:\n"
                    f"Имя: {user.first_name} {user.last_name or ''}\n"
                    f"Username: @{user.username or 'отсутствует'}\n"
                    f"ID: {user_id}",
                )
            except Exception as e2:
                logger.error(f"Повторная ошибка при отправке уведомления: {e2}")


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


# Обработчик сообщений от пользователей
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает сообщения пользователей."""
    user = update.effective_user
    user_id = user.id
    message_text = update.message.text

    # Инициализация истории сообщений для нового пользователя
    if user_id not in user_messages:
        user_messages[user_id] = []

    # Добавление сообщения в историю
    user_messages[user_id].append(f"Пользователь: {message_text}")

    # Если сообщение от пользователя (не от админа)
    if user_id != ADMIN_ID:
        # Создаем кнопку для ответа
        keyboard = [
            [InlineKeyboardButton("Ответить", callback_data=f"reply_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем сообщение администратору
        try:
            await safe_send_message(
                context=context,
                chat_id=ADMIN_ID,
                text=f"Сообщение от пользователя:\n"
                f"Имя: {user.first_name} {user.last_name or ''}\n"
                f"Username: @{user.username or 'отсутствует'}\n"
                f"ID: {user_id}\n\n"
                f"Сообщение: {message_text}",
                reply_markup=reply_markup,
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
    elif user_id == ADMIN_ID and not context.user_data.get("replying_to"):
        await update.message.reply_text(
            "Чтобы ответить пользователю, используйте кнопку 'Ответить' под его сообщением."
        )


# Обработчик кнопки "Ответить"
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатие на кнопку 'Ответить'."""
    query = update.callback_query
    await query.answer()

    # Получаем ID пользователя из callback_data
    data = query.data
    if data.startswith("reply_"):
        user_id = int(data.split("_")[1])

        # Сохраняем ID пользователя, которому отвечаем
        context.user_data["replying_to"] = user_id

        # Показываем историю переписки
        history = "\n".join(user_messages.get(user_id, []))

        try:
            await query.edit_message_text(
                text=f"Вы отвечаете пользователю с ID {user_id}.\n\n"
                f"История переписки:\n{history}\n\n"
                f"Напишите ваш ответ (или /cancel для отмены):"
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения: {e}")
            # Отправляем новое сообщение, если не можем обновить существующее
            await safe_send_message(
                context=context,
                chat_id=update.effective_user.id,
                text=f"Вы отвечаете пользователю с ID {user_id}.\n\n"
                f"История переписки:\n{history}\n\n"
                f"Напишите ваш ответ (или /cancel для отмены):",
            )


# Обработчик ответа администратора
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ответ администратора на сообщение пользователя."""
    user_id = update.effective_user.id

    # Проверяем, что это администратор и что он отвечает кому-то
    if user_id == ADMIN_ID and context.user_data.get("replying_to"):
        reply_to_id = context.user_data["replying_to"]
        message_text = update.message.text

        # Если админ хочет отменить ответ
        if message_text == "/cancel":
            del context.user_data["replying_to"]
            await update.message.reply_text("Ответ отменен.")
            return

        # Добавляем ответ в историю переписки
        if reply_to_id in user_messages:
            user_messages[reply_to_id].append(f"Администратор: {message_text}")

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


# Обработчик команды /list для отображения списка всех пользователей
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает список всех пользователей, которые писали боту."""
    user_id = update.effective_user.id

    # Проверяем, что это администратор
    if user_id == ADMIN_ID:
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


# Обработчик команды /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отображает справочную информацию."""
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "Команды администратора:\n"
            "/start - Начать работу с ботом\n"
            "/list - Показать список всех пользователей\n"
            "/help - Показать эту справку\n\n"
            "Для ответа пользователю используйте кнопку 'Ответить' под его сообщением."
        )
    else:
        await update.message.reply_text(
            "Просто напишите ваше сообщение, и администратор ответит вам, как только сможет."
        )


# Обработчик ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Логирует ошибки, вызванные обновлениями."""
    logger.error(f"Возникла ошибка: {context.error}", exc_info=context.error)

    # Если обновление доступно, отправляем сообщение об ошибке
    if update and hasattr(update, "effective_user") and update.effective_user:
        if update.effective_user.id == ADMIN_ID:
            error_message = (
                f"Произошла ошибка при обработке обновления: {context.error}"
            )
            try:
                await safe_send_message(context, ADMIN_ID, error_message)
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

        # Добавляем обработчик для кнопок
        application.add_handler(CallbackQueryHandler(callback_handler))

        # Специальный обработчик для ответов администратора
        admin_reply_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), admin_reply
        )
        application.add_handler(admin_reply_handler)

        # Общий обработчик сообщений
        message_handler = MessageHandler(
            filters.TEXT & ~filters.COMMAND, handle_message
        )
        application.add_handler(message_handler)

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
