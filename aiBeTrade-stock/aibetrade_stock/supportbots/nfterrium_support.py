from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
import sys
import os
from pymongo import MongoClient
from datetime import datetime, UTC
from nfterrium_chat_helping import bot_chat_user, handle_support_reply, handle_edited_message, handle_deleted_message, SUPPORT_GROUP_ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('NfterriumBot')

# Подключение к MongoDB
MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(MONGO_URI)
db = client.nntcapital

# Языковые настройки
LANGUAGES = {
    'en': 'English 🇬🇧',
    'ru': 'Русский 🇷🇺'
}

# Тексты для разных языков
TEXTS = {
    'ru': {
        'welcome': """
Welcome to support service Nfterrium!
Choose your language

Добро пожаловать в службу поддержки Nfterrium!
Выберите язык общения
        """,
        'language_selected': "Язык успешно изменен на Русский 🇷🇺",
        'help_message': """
Это бот поддержки Nfterrium. Отправьте ваше сообщение, и мы ответим вам в ближайшее время.
        """
    },
    'en': {
        'welcome': """
Welcome to support service Nfterrium!
Choose your language:
        """,
        'language_selected': "Language successfully changed to English 🇬🇧",
        'help_message': """
This is a support bot Nfterrium. Send your message and we will reply as soon as possible.
        """
    }
}

def init_db():
    """
    Инициализация базы данных
    """
    try:
        # Создаем коллекцию для пользовательских настроек если её нет
        if 'nfterrium_user_settings' not in db.list_collection_names():
            db.create_collection('nfterrium_user_settings')
        
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}", exc_info=True)

def get_user_language(user_id: int) -> str:
    """
    Получает язык пользователя из БД
    """
    try:
        user_settings = db.nfterrium_user_settings.find_one({'user_id': user_id})
        return user_settings['language'] if user_settings else 'ru'
    except Exception as e:
        logger.error(f"Ошибка при получении языка пользователя: {e}", exc_info=True)
        return 'ru'

def save_user_language(user_id: int, language: str):
    """
    Сохраняет язык пользователя в БД
    """
    try:
        db.nfterrium_user_settings.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'language': language,
                'updated_at': datetime.now(UTC)
            }},
            upsert=True
        )
        logger.info(f"Сохранен язык пользователя {user_id}: {language}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении языка пользователя: {e}", exc_info=True)

def get_language_keyboard() -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора языка
    """
    keyboard = InlineKeyboardMarkup()
    for lang_code, lang_name in LANGUAGES.items():
        keyboard.add(InlineKeyboardButton(
            text=lang_name,
            callback_data=f'lang_{lang_code}'
        ))
    return keyboard

def run_support_bot(token: str):
    """
    Запуск бота поддержки
    """
    bot = TeleBot(token)
    
    @bot.message_handler(commands=['start'])
    def start_command(message: Message):
        """
        Обработка команды /start
        """
        try:
            # Отправляем приветственное сообщение с выбором языка
            bot.send_message(
                message.chat.id,
                TEXTS['en']['welcome'],
                reply_markup=get_language_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке команды start: {e}", exc_info=True)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
    def language_callback(call):
        """
        Обработка выбора языка
        """
        try:
            language = call.data.split('_')[1]
            user_id = call.from_user.id
            
            # Сохраняем выбранный язык
            save_user_language(user_id, language)
            
            # Отправляем сообщение о смене языка
            bot.edit_message_text(
                TEXTS[language]['language_selected'],
                call.message.chat.id,
                call.message.message_id
            )
            
            # Отправляем приветственное сообщение на выбранном языке
            bot.send_message(
                call.message.chat.id,
                TEXTS[language]['help_message']
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке выбора языка: {e}", exc_info=True)
    
    @bot.message_handler(commands=['help'])
    def help_command(message: Message):
        """
        Обработка команды /help
        """
        try:
            language = get_user_language(message.from_user.id)
            bot.reply_to(message, TEXTS[language]['help_message'])
        except Exception as e:
            logger.error(f"Ошибка при обработке команды help: {e}", exc_info=True)
    
    @bot.message_handler(func=lambda message: message.chat.id != SUPPORT_GROUP_ID and not message.text.startswith('/'))
    def user_message_handler(message: Message):
        """
        Обработка сообщений от пользователей
        """
        try:
            bot_chat_user(message, bot)
        except Exception as e:
            logger.error(f"Ошибка при обработке сообщения пользователя: {e}", exc_info=True)
            language = get_user_language(message.from_user.id)
            bot.reply_to(message, TEXTS[language]['help_message'])
    
    @bot.message_handler(func=lambda message: message.chat.id == SUPPORT_GROUP_ID and message.reply_to_message)
    def support_reply_handler(message: Message):
        """
        Обработка ответов от поддержки
        """
        try:
            handle_support_reply(message, bot)
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа поддержки: {e}", exc_info=True)
    
    @bot.edited_message_handler(func=lambda message: message.chat.id != SUPPORT_GROUP_ID)
    def on_edit(message: Message):
        """
        Обработка редактирования сообщений
        """
        try:
            handle_edited_message(message, bot)
        except Exception as e:
            logger.error(f"Ошибка при обработке редактирования сообщения: {e}", exc_info=True)
    
    @bot.message_handler(content_types=['delete_chat_message'])
    def on_delete(message: Message):
        """
        Обработка удаления сообщений
        """
        try:
            handle_deleted_message(message, bot)
        except Exception as e:
            logger.error(f"Ошибка при обработке удаления сообщения: {e}", exc_info=True)
    
    # Инициализируем базу данных
    init_db()
    
    # Запускаем бота
    logger.info("Бот запущен...")
    bot.infinity_polling()

if __name__ == "__main__":
    TOKEN = os.getenv('BOT_TOKEN')  # или ваш способ получения токена
    if not TOKEN:
        raise ValueError("Не удалось получить токен бота")
    run_support_bot(TOKEN)

