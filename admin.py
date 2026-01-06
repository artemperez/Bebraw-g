from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from config import ADMIN_IDS
from database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ панель"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У вас нет доступа к админ панели!")
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("📢 Добавить канал", callback_data="add_channel")],
        [InlineKeyboardButton("🗑️ Удалить канал", callback_data="remove_channel")],
        [InlineKeyboardButton("📋 Список каналов", callback_data="list_channels")],
        [InlineKeyboardButton("📤 Рассылка", callback_data="broadcast")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💻 Админ панель\n\n"
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-ов админ панели"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ У вас нет доступа!")
        return
    
    if query.data == "stats":
        stats = db.get_stats()
        await query.edit_message_text(
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"📢 Всего каналов: {stats['total_channels']}"
        )
    
    elif query.data == "list_channels":
        channels = db.get_all_channels()
        if not channels:
            await query.edit_message_text("📭 Список каналов пуст")
            return
        
        channels_list = "\n".join([f"• {name} (ID: {cid})" for cid, name in channels])
        await query.edit_message_text(f"📋 Список каналов:\n\n{channels_list}")
    
    elif query.data == "add_channel":
        await query.edit_message_text(
            "📢 Для добавления канала отправьте сообщение в формате:\n"
            "`@username_channel Название канала`\n\n"
            "Или:\n"
            "`-1001234567890 Название канала`",
            parse_mode="Markdown"
        )
        context.user_data['waiting_for_channel'] = True
    
    elif query.data == "remove_channel":
        channels = db.get_all_channels()
        if not channels:
            await query.edit_message_text("📭 Список каналов пуст")
            return
        
        keyboard = [
            [InlineKeyboardButton(f"{name}", callback_data=f"remove_{cid}")]
            for cid, name in channels
        ]
        keyboard.append([InlineKeyboardButton("« Назад", callback_data="back_to_admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗑️ Выберите канал для удаления:",
            reply_markup=reply_markup
        )
    
    elif query.data == "broadcast":
        await query.edit_message_text(
            "📤 Отправьте сообщение для рассылки всем пользователям:"
        )
        context.user_data['waiting_for_broadcast'] = True
    
    elif query.data == "back_to_admin":
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton("📢 Добавить канал", callback_data="add_channel")],
            [InlineKeyboardButton("🗑️ Удалить канал", callback_data="remove_channel")],
            [InlineKeyboardButton("📋 Список каналов", callback_data="list_channels")],
            [InlineKeyboardButton("📤 Рассылка", callback_data="broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👨‍💻 Админ панель\n\n"
            "Выберите действие:",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith("remove_"):
        channel_id = query.data.replace("remove_", "")
        db.remove_channel(channel_id)
        await query.edit_message_text(f"✅ Канал удален: {channel_id}")
    
    elif query.data == "confirm_broadcast":
        message = context.user_data.get('broadcast_message')
        if message:
            # Здесь будет код рассылки
            await query.edit_message_text("✅ Рассылка начата!")
        else:
            await query.edit_message_text("❌ Сообщение для рассылки не найдено")

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений для админов"""
    user_id = update.effective_user.id
    message_text = update.message.text
    
    if not is_admin(user_id):
        return
    
    if context.user_data.get('waiting_for_channel'):
        try:
            parts = message_text.split(' ', 1)
            if len(parts) != 2:
                await update.message.reply_text("❌ Неверный формат!")
                return
            
            channel_id, channel_name = parts
            if db.add_channel(channel_id, channel_name, user_id):
                await update.message.reply_text(f"✅ Канал добавлен: {channel_name}")
            else:
                await update.message.reply_text("❌ Ошибка при добавлении канала")
            
            context.user_data.pop('waiting_for_channel', None)
            
        except Exception as e:
            logger.error(f"Error adding channel: {e}")
            await update.message.reply_text("❌ Ошибка при обработке запроса")
    
    elif context.user_data.get('waiting_for_broadcast'):
        context.user_data['broadcast_message'] = message_text
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ Отмена", callback_data="back_to_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📤 Подтвердите рассылку:\n\n{message_text}\n\n"
            f"Это сообщение будет отправлено всем пользователям.",
            reply_markup=reply_markup
        )
        context.user_data.pop('waiting_for_broadcast', None)

# Регистрация обработчиков
def get_admin_handlers():
    return [
        CommandHandler("admin", admin_panel),
        CallbackQueryHandler(admin_callback_handler),
    ]