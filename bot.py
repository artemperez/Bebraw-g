import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from config import BOT_TOKEN, ADMIN_IDS, PRIVATE_LINKS
from database import Database
from admin import get_admin_handlers, handle_admin_message

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = (
        "👋 *Добро пожаловать!*\n\n"
        "🚀 Чтобы получить доступ к приватным каналам, "
        "необходимо подписаться на следующие каналы:\n\n"
    )
    
    # Получаем список каналов из базы данных
    channels = db.get_all_channels()
    
    if not channels:
        welcome_text += "📭 Каналы еще не добавлены администратором.\n"
        await update.message.reply_text(welcome_text, parse_mode="Markdown")
        return
    
    # Формируем список каналов
    for idx, (channel_id, channel_name) in enumerate(channels, 1):
        welcome_text += f"{idx}. {channel_name}\n"
    
    welcome_text += "\n✅ После подписки на все каналы нажмите кнопку 'Проверить подписку'"
    
    # Кнопка для проверки подписки
    keyboard = [[InlineKeyboardButton("🔍 Проверить подписку", callback_data="check_subscription")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Проверка подписки на каналы"""
    if not user_id:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
    else:
        query = None
    
    channels = db.get_all_channels()
    
    if not channels:
        message = "📭 Каналы еще не добавлены администратором."
        if query:
            await query.edit_message_text(message)
        return
    
    # Проверяем подписку на каждый канал
    bot = context.bot
    not_subscribed = []
    
    for channel_id, channel_name in channels:
        try:
            # Пытаемся получить статус пользователя в канале
            chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if chat_member.status in ['left', 'kicked']:
                not_subscribed.append((channel_id, channel_name))
        except Exception as e:
            logger.error(f"Error checking subscription for {channel_id}: {e}")
            not_subscribed.append((channel_id, channel_name))
    
    if not_subscribed:
        # Формируем сообщение с кнопками для подписки
        message = "❌ *Вы не подписаны на следующие каналы:*\n\n"
        keyboard = []
        
        for channel_id, channel_name in not_subscribed:
            message += f"• {channel_name}\n"
            # Создаем кнопку для подписки
            keyboard.append([InlineKeyboardButton(
                f"📢 Подписаться на {channel_name}", 
                url=f"https://t.me/{channel_id.replace('@', '')}"
            )])
        
        message += "\n✅ Подпишитесь на все каналы и нажмите кнопку ниже для проверки"
        keyboard.append([InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_subscription")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.edit_message_text(
                message,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        return False
    else:
        # Пользователь подписан на все каналы
        message = (
            "✅ *Отлично! Вы подписаны на все каналы!*\n\n"
            "🎉 *Вот ваши приватные ссылки:*\n\n"
        )
        
        # Добавляем приватные ссылки
        for idx, link in enumerate(PRIVATE_LINKS[:50], 1):  # Ограничиваем 50 ссылками
            message += f"{idx}. {link}\n"
        
        if len(PRIVATE_LINKS) > 50:
            message += f"\n... и еще {len(PRIVATE_LINKS) - 50} ссылок!\n"
        
        message += "\n🔥 *Приятного пользования!*"
        
        # Обновляем статус подписки пользователя
        subscribed_channels = [cid for cid, _ in channels]
        db.update_user_subscription(user_id, subscribed_channels)
        
        if query:
            await query.edit_message_text(
                message,
                parse_mode="Markdown",
                disable_web_page_preview=True
            )
        return True

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов"""
    query = update.callback_query
    data = query.data
    
    if data == "check_subscription":
        await check_subscription(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🤖 *Помощь по боту*\n\n"
        "📌 *Доступные команды:*\n"
        "/start - Начать работу с ботом\n"
        "/help - Получить помощь\n"
        "/links - Получить приватные ссылки (если подписан)\n\n"
        "📢 *Как получить доступ:*\n"
        "1. Подпишитесь на все указанные каналы\n"
        "2. Нажмите 'Проверить подписку'\n"
        "3. Получите доступ к приватным каналам!"
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def get_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /links для получения ссылок"""
    user_id = update.effective_user.id
    
    # Проверяем подписку
    if await check_subscription(update, context, user_id):
        # Если пользователь подписан, сообщение уже отправлено в check_subscription
        return
    
    # Если не подписан, отправляем инструкцию
    await update.message.reply_text(
        "❌ Вы еще не подписаны на все каналы.\n"
        "Используйте /start для проверки подписки."
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("links", get_links))
    
    # Регистрируем обработчики админ панели
    for handler in get_admin_handlers():
        application.add_handler(handler)
    
    # Обработчик сообщений для админов
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_admin_message
    ))
    
    # Регистрируем обработчик callback-запросов
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()