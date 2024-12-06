import telebot
from telebot import types
from datetime import datetime
from pymongo import MongoClient
import os
import langdetect
import logging
from bits_info import create_info_menu, get_info_texts, handle_info_section
from bits_status import get_status_user, handle_new_connection
from bits_chat_helping import bot_chat_user, handle_support_reply, SUPPORT_GROUP_ID, handle_edited_message, handle_deleted_message
import sys
# Укажите токен вашего бота
# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
client = MongoClient(mongo_url)
db = client["nntcapital"]
bits_settings = db["bits_settings"]
bits_user_settings = db["bits_user_settings"]

# Хранит состояние выбранного раздела и текст сообщения
user_state = {}

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BitsBot')

# Получение разрешенных пользователей
def get_ket_bot():
    try:
        bot_key = bits_settings.find_one({})
        if not bot_key:
            return None
        return bot_key.get('bot_key_test')
    except Exception as e:
        print(f"Ошибка при получении списка разрешенных пользователей: {str(e)}")
        return None

# Определение языка пользователя
def detect_language(text):
    try:
        return langdetect.detect(text)
    except:
        return 'en'  # По умолчанию английский

# Функция для создания inline-кнопок главного меню с учетом языка
def create_lang_menu(lang='en'):
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("🇺🇸 English", callback_data="eng"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="rus"),
        types.InlineKeyboardButton("🇫🇷 Français", callback_data="fra"),
        types.InlineKeyboardButton("🇩🇪 Deutsch", callback_data="deu"),
        types.InlineKeyboardButton("🇪🇸 Español", callback_data="esp"),
        types.InlineKeyboardButton("🇨🇳 中文", callback_data="lang_zh")
    ]
    markup.add(*buttons)
    return markup
# Функция для создания inline-кнопок главного меню с учетом языка
def create_main_menu(lang='en'):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    menu_buttons = {
        'ru': [
            ("🛠️ Помощь", "help"),
            ("ℹ️ Информация", "info"),
            ("🔔 Статистика", "status"),
            ("🌐 Язык", "lang")
        ],
        'en': [
            ("🛠️ Help", "help"),
            ("ℹ️ Information", "info"),
            ("🔔 Status", "status"),
            ("🌐 Language", "lang")
        ],
        'fra': [
            ("🛠️ Aide", "help"),
            ("ℹ️ Information", "info"),
            ("🔔 Statistiques", "status"),
            ("🌐 Langue", "lang")
        ],
        'deu': [
            ("🛠️ Hilfe", "help"),
            ("ℹ️ Information", "info"),
            ("🔔 Statistiken", "status"),
            ("🌐 Sprache", "lang")
        ],
        'esp': [
            ("🛠️ Ayuda", "help"),
            ("ℹ️ Información", "info"),
            ("🔔 Estadísticas", "status"),
            ("🌐 Idioma", "lang")
        ],
        'lang_zh': [
            ("🛠️ 帮助", "help"),
            ("ℹ️ 信息", "info"),
            ("🔔 统计", "status"),
            ("🌐 语言", "lang")
        ]
    }
    
    buttons = menu_buttons.get(lang, menu_buttons['en'])
    button_pairs = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    
    for pair in button_pairs:
        row_buttons = [types.InlineKeyboardButton(text, callback_data=data) for text, data in pair]
        markup.row(*row_buttons)
    
    return markup

# Инициализация бота
TOKEN = get_ket_bot()
if not TOKEN:
    raise ValueError("Не удалось получить токен бота")
bot = telebot.TeleBot(TOKEN)

# Устновка команд меню бота
def setup_bot_commands():
    try:
        # Команды для разных языков
        commands = {
            "ru": [
                telebot.types.BotCommand("start", "Запустить бота"),
                telebot.types.BotCommand("help", "Помощь"),
                telebot.types.BotCommand("language", "Выбор языка"),
                telebot.types.BotCommand("status", "Статус сервисов"),
                telebot.types.BotCommand("info", "Информация о боте")
            ],
            "en": [
                telebot.types.BotCommand("start", "Start the bot"),
                telebot.types.BotCommand("help", "Help"),
                telebot.types.BotCommand("language", "Choose language"),
                telebot.types.BotCommand("status", "Service status"),
                telebot.types.BotCommand("info", "Information")
            ],
            "fra": [
                telebot.types.BotCommand("start", "Démarrer le bot"),
                telebot.types.BotCommand("help", "Aide"),
                telebot.types.BotCommand("language", "Choisir la langue"),
                telebot.types.BotCommand("status", "État des services"),
                telebot.types.BotCommand("info", "Information")
            ],
            "deu": [
                telebot.types.BotCommand("start", "Bot starten"),
                telebot.types.BotCommand("help", "Hilfe"),
                telebot.types.BotCommand("language", "Sprache wählen"),
                telebot.types.BotCommand("status", "Servicestatus"),
                telebot.types.BotCommand("info", "Bot-Information")
            ],
            "esp": [
                telebot.types.BotCommand("start", "Iniciar el bot"),
                telebot.types.BotCommand("help", "Ayuda"),
                telebot.types.BotCommand("language", "Elegir idioma"),
                telebot.types.BotCommand("status", "Estado del servicio"),
                telebot.types.BotCommand("info", "Información del bot")
            ]
        }
        
        # Устанавливаем команды для каждого языка
        for lang_code, lang_commands in commands.items():
            bot.set_my_commands(lang_commands, language_code=lang_code)
        
        print("Команды меню бота успешно установлены")
    except Exception as e:
        print(f"Ошибка при установке команд меню: {str(e)}")

# Обработчики команд
@bot.message_handler(commands=['help'])
def handle_help(message):
    # Получаем настройки пользователя из базы данных
    user_settings = bits_user_settings.find_one({'user_id': message.from_user.id})
    # Используем язык из настроек или английский по умолчанию
    user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
    
    help_texts = {
        'ru': """
🤖 Доступные команды:
/start - Запустить бота
/help - Показать это сообщение
/language - Выбрать язык
/status - Статус сервисов
/info - Информация о боте
""",
        'fra': """
🤖 Commandes disponibles:
/start - Démarrer le bot
/help - Afficher ce message
/language - Choisir la langue
/status - État des services
/info - Information sur le bot
""",
        'deu': """
🤖 Verfügbare Befehle:
/start - Bot starten
/help - Diese Nachricht anzeigen
/language - Sprache wählen
/status - Servicestatus
/info - Bot-Information
""",
        'esp': """
🤖 Comandos disponibles:
/start - Iniciar el bot
/help - Mostrar este mensaje
/language - Elegir idioma
/status - Estado del servicio
/info - Información del bot
""",
        'lang_zh': """
🤖 可用命令：
/start - 启动机器人
/help - 显示此消息
/language - 选择语言
/status - 服务状态
/info - 机器人信息
""",
        'en': """
🤖 Available commands:
/start - Start the bot
/help - Show this message
/language - Choose language
/status - Service status
/info - Bot information
"""
    }
    
    bot.send_message(message.chat.id, help_texts.get(user_lang, help_texts['en']))
    print(f"Пользователь {message.from_user.id} использовал команду /help на языке {user_lang}")

@bot.message_handler(commands=['language'])
def handle_language(message):
    bot.send_message(
        message.chat.id,
        "Select language / Выберите язык / Choisissez la langue / Wählen Sie die Sprache / Seleccione el idioma:",
        reply_markup=create_lang_menu()
    )

@bot.message_handler(commands=['status'])
def handle_status(message, user_id, user_lang):
    logger.info(f"handle_status вызван для user_id: {user_id}, язык: {user_lang}")
    
    user_settings = bits_user_settings.find_one({'user_id': user_id})
    user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
    
    status_texts = {
        'ru': "🔄 Проверка статуса сервисов...",
        'fra': "🔄 Vérification de l'état des services...",
        'deu': "🔄 Überprüfung des Servicestatus...",
        'esp': "🔄 Comprobando el estado del servicio...",
        'en': "🔄 Checking service status..."
    }
    
    logger.info(f"Возвращаем пользователя к списку подключений для user_id: {user_id}, язык: {user_lang}")

    # Получаем статус
    status_texts_bot = get_status_user(message, bot, user_lang, user_id)
    
    # Проверяем, что status_texts_bot не None
    if status_texts_bot is None:
        logger.error(f"get_status_user вернул None для user_id: {user_id}")
        status_texts_bot = {
            'ru': "❌ Ошибка при получении статуса",
            'fra': "❌ Erreur lors de l'obtention du statut",
            'deu': "❌ Fehler beim Abrufen des Status",
            'esp': "❌ Error al obtener el estado",
            'en': "❌ Error getting status"
        }.get(user_lang, "❌ Error getting status")
    
    # Формируем полное сообщение
    full_message = f"{status_texts.get(user_lang, status_texts['en'])}\n\n{status_texts_bot}"
    
    logger.info(f"Отправляем сообщение о статусе для user_id: {user_id}")
    bot.send_message(message.chat.id, full_message)

@bot.message_handler(commands=['info'])
def handle_info(message):
    
    user_settings = bits_user_settings.find_one({'user_id': message.from_user.id})
    
    user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
    
    info_texts = {
        'ru': "ℹ️ Информация о боте и его возможностях",
        'fra': "ℹ️ Informations sur le bot et ses capacités",
        'deu': "ℹ️ Informationen über den Bot und seine Fähigkeiten",
        'esp': "ℹ️ Información sobre el bot y sus capacidades",
        'en': "ℹ️ Information about the bot and its capabilities"
    }
    text_info = get_info_texts(user_lang)
    
    bot.send_message(message.chat.id, info_texts.get(user_lang, info_texts['en']) + "\n\n" + text_info)

def welcome_text_lang(lang):
    welcome_texts = {
        'ru': (
            "Привет, мой друг! 👋\n\n"
            "Я твой персональный помощник в мире трейдинга. "
            "Я помогу тебе отслеживать сигналы, управлять портфелем "
            "и быть в курсе всех важных событий на рынке.\n\n"
        ),
        'lang_zh': (
            "你好，我的朋友！👋\n\n"
            "我是你的个人交易助理。我将帮助你跟踪信号、管理你的投资组合，并随时了解所有重要的市场事件。\n\n"
        ),
        'fra': (
            "Bonjour, mon ami! 👋\n\n"
            "Je suis votre assistant de trading personnel. Je vous aidera à suivre les signaux, "
            "gérer votre portefeuille et rester à jour avec tous les événements importants du marché.\n\n"
        ),
        'deu': (
            "Hallo, mein Freund! 👋\n\n"
            "Ich bin Ihr persönlicher Handelsassistent. Ich werde Ihnen helfen, die Signale zu verfolgen, "
            "Ihr Portfolio zu verwalten und stets über alle wichtigen Marktveranstaltungen auf dem Laufenden zu bleiben.\n\n"
        ),
        'esp': (
            "¡Hola, mi amigo! 👋\n\n"
            "Soy tu asistente de trading personal. Te ayudaré a seguir las señales, "
            "gestionar tu cartera y mantenerte al margen de todos los eventos importantes del mercado.\n\n"
        ),
        'en': (
            "Hello, my friend! 👋\n\n"
            "I'm your personal trading assistant. "
            "I'll help you track signals, manage your portfolio, "
            "and stay updated with all important market events.\n\n"
        )
    }
    return welcome_texts.get(lang, welcome_texts['en'])

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        # Проверяем, есть ли пользователь в базе
        user_system = bits_user_settings.find_one({'user_id': message.from_user.id})
        
        if not user_system:
            # Новый пользователь - предлагаем выбрать язык
            select_language_text = (
                "👋 Welcome! Please select your language\n"
                "👋 Здравствуйте! Пожалуйста, выберите ваш язык\n"
                "👋 Bonjour! Veuillez choisir votre langue\n"
                "👋 Hallo! Bitte wählen Sie Ihre Sprache\n"
                "👋 ¡Hola! Por favor, seleccione su idioma\n"
                "👋 你好！请选择你的语言"
            )
            
            # Отправляем меню выбора языка
            bot.send_message(
                message.chat.id,
                select_language_text,
                reply_markup=create_lang_menu()
            )
        else:
            # Существующий пользователь - используем сохраненный язык
            user_lang = user_system.get('lang_set', 'en')
            welcome_text = welcome_text_lang(user_lang)
            
            # Тексты для меню на разных языках
            menu_texts = {
                'ru': "Выберите нужное действие:",
                'en': "Please select an action:",
                'fra': "Veuillez sélectionner une action:",
                'deu': "Bitte wählen Sie eine Aktion:",
                'esp': "Por favor, seleccione una acción:",
                'lang_zh': "请选择操作："
            }
            
            # Отправляем приветствие и меню на языке пользователя
            bot.send_message(
                message.chat.id,
                f"{welcome_text}\n\n{menu_texts.get(user_lang, menu_texts['en'])}",
                reply_markup=create_main_menu(user_lang)
            )
            
    except Exception as e:
        print(f"Ошибка при обработке команды start: {str(e)}")
        bot.reply_to(message, "An error occurred. Please try again later.")

# Обработчик callback-запросов от inline-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    try:
        # Получаем текущий язык пользователя
        user_settings = bits_user_settings.find_one({'user_id': call.from_user.id})
        user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
        
        logger.info(f"Получен callback: {call.data} от пользователя {call.from_user.id}")

# В обработчике callback для create_account добавьте:
        if call.data == "create_account":
            logger.info(f"Обработка create_account для пользователя {call.from_user.id}")
            user_states[call.from_user.id] = {
                'creating_account': True,
                'step': 'exchange',
                'user_id': call.from_user.id
            }
            handle_new_connection(
                message=call.message,
                bot=bot,
                state=user_states[call.from_user.id],
                lang=user_lang,
                user_id=call.from_user.id
            )

        elif call.data == "back_to_main":
            logger.info(f"Обработка back_to_main для пользователя {call.from_user.id}")
            # Возвращаем пользователя в главное меню
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Выберите действие:",
                reply_markup=create_main_menu(user_lang)
            )
            return
        
        elif call.data.startswith("exchange_"):
            logger.info(f"Обработка create_account для пользователя {call.from_user.id}")
            # Инициализируем состояние пользователя
            if not hasattr(bot, 'user_states'):
                bot.user_states = {}
            
            bot.user_states[call.from_user.id] = {
                'step': 'key',
                'user_id': call.from_user.id
            }
            
            # Вызываем handle_new_connection из bits_status
            handle_new_connection(
                message=call.message,
                bot=bot,
                state=bot.user_states[call.from_user.id],
                lang=user_lang,
                user_id=call.from_user.id
            )
            return
        # Обработка информационного меню
        if call.data == "info":
            # Удаляем предыдущее сообщение
            bot.delete_message(call.message.chat.id, call.message.message_id)
            
            # Получаем тексты ля текущго языка
            texts = get_info_texts(user_lang)
            
            # Отправляем заголовок информационного меню с кнопками
            bot.send_message(
                call.message.chat.id,
                texts['menu_title'],
                reply_markup=create_info_menu(user_lang),
                parse_mode='HTML'
            )
            
        # Обработка разделов информационного меню
        elif call.data.startswith("info_"):
            # Удаляем предыдущее сообщение
            bot.delete_message(call.message.chat.id, call.message.message_id)
            
            # Получаем название раздела
            section = call.data.split("_")[1]
            
            # Обрабатываем выбранный раздел
            result = handle_info_section(bot, call.message, user_lang, section)
            
            # Если это кнопка "назад", возвращаемся в главное меню
            if result == "back":
                bot.send_message(
                    call.message.chat.id,
                    "Выберите действие:",
                    reply_markup=create_main_menu(user_lang)
                )
        
        # Обработка выбора языка и других callback-запросов
        elif call.data in ["rus", "eng", "fra", "deu", "esp", "lang_zh"]:
            # Маппинг кодов языков из кнопок в коды для системы
            lang_mapping = {
                "rus": "ru",
                "eng": "en",
                "fra": "fra",
                "deu": "deu",
                "esp": "esp",
                "lang_zh": "lang_zh"
            }
            selected_lang = lang_mapping[call.data]
            
            # Проверяем, есть ли пользователь в базе
            user_exists = bits_user_settings.find_one({'user_id': call.from_user.id})
            
            if not user_exists:
                # Создаем новую запись для пользователя
                user_data = {
                    'user_id': call.from_user.id,
                    'username': call.from_user.username,
                    'timestamp': datetime.now(),
                    'lang': selected_lang,
                    'lang_set': selected_lang
                }
                bits_user_settings.insert_one(user_data)
            else:
                # Обновляем язык для существующего пользователя
                bits_user_settings.update_one(
                    {'user_id': call.from_user.id},
                    {'$set': {'lang_set': selected_lang}}
                )
            
            # Подтверждение выбора языка
            confirmation_texts = {
                'ru': "✅ Язык успешно изменен на Русский",
                'en': "✅ Language successfully changed to English",
                'fra': "✅ Langue changée avec succès en Français",
                'deu': "✅ Sprache erfolgreich auf Deutsch geändert",
                'esp': "✅ Idioma cambiado exitosamente a Español",
                'lang_zh': "✅ 语言已成功更改为中文"
            }
            
            # Отправляем подтверждение
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=confirmation_texts.get(selected_lang, confirmation_texts['en'])
            )
            
            # Отправляем основное меню на выбранном языке
            menu_texts = {
                'ru': "Выберит нужное действие:",
                'en': "Please select an action:",
                'fra': "Veuillez sélectionner une action:",
                'deu': "Bitte wählen Sie eine Aktion:",
                'esp': "Por favor, seleccione una acción:",
                'lang_zh': "请选择操作："
            }
            
            bot.send_message(
                call.message.chat.id,
                menu_texts.get(selected_lang, menu_texts['en']),
                reply_markup=create_main_menu(selected_lang)
            )
            
        # Обработка других кнопок меню
        elif call.data in ["help", "info", "status", "lang"]:
            # Получаем текущий язык пользователя
            user_settings = bits_user_settings.find_one({'user_id': call.from_user.id})
            user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
            
            if call.data == "help":
                handle_help(call.message)
            elif call.data == "info":
                handle_info(call.message)
            elif call.data == "status":
                handle_status(call.message,call.from_user.id,user_lang)
            elif call.data == "lang":
                # Показываем меню выбора языка
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="🌐 Select language / Выберите язык / Choisissez la langue / Wählen Sie die Sprache / Seleccione el idioma / 选择语言",
                    reply_markup=create_lang_menu()
                )
                
    except Exception as e:
        logger.error(f"Ошибка при обработке callback {call.data}: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")

@bot.message_handler(func=lambda message: message.chat.id != SUPPORT_GROUP_ID and not message.text.startswith('/'))

def message_handler(message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    
    # Проверяем, находится ли пользователь в процессе создания аккаунта
    if user_id in user_states and 'creating_account' in user_states[user_id]:
        handle_account_creation(message)
    else:
        # Если пользователь не в процессе создания аккаунта, 
        # обрабатываем как обычное сообщение в поддержку
        bot_chat_user(message, bot)

def handle_account_creation(message):
    """Обработка сообщений при создании аккаунта"""
    user_id = message.from_user.id
    state = user_states[user_id]
    user_lang = get_user_language(user_id)
    
    logger.info(f"Обработка создания аккаунта для user_id: {user_id}, state: {state}")
    
    try:
        if state['step'] == 'key':
            key = message.text.strip()
            if len(key) != 10:
                bot.reply_to(message, TEXTS[user_lang]['invalid_key'])
                return
            state['key'] = key
            state['step'] = 'secret'
            bot.reply_to(message, TEXTS[user_lang]['enter_secret'])
            
        elif state['step'] == 'secret':
            secret = message.text.strip()
            if len(secret) != 15:
                bot.reply_to(message, TEXTS[user_lang]['invalid_secret'])
                return
            state['secret_key'] = secret
            state['step'] = 'deposit'
            bot.reply_to(message, TEXTS[user_lang]['enter_deposit'])
            
        elif state['step'] == 'deposit':
            try:
                deposit = float(message.text.strip())
                if deposit < 1000:
                    bot.reply_to(message, TEXTS[user_lang]['invalid_deposit'])
                    return
                
                # Создаем новую запись в БД
                connection_data = {
                    'user_id': user_id,
                    'connection_id': f"CONN_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    'stock': state['exchange'],
                    'key': state['key'],
                    'secret_key': state['secret_key'],
                    'start_dep': deposit,
                    'start_data': datetime.now(UTC),
                    'pay_period': 30 if deposit < 10000 else 90,
                    'share_profit': 30 if deposit < 10000 else (25 if deposit < 50000 else 20)
                }
                
                db.bits_user_connection.insert_one(connection_data)
                
                # Отправляем информацию о созданном подключении
                bot.reply_to(
                    message,
                    TEXTS[user_lang]['connection_info'].format(**connection_data),
                    reply_markup=create_connection_menu(connection_data, user_lang)
                )
                
                # Очищаем состояние
                del user_states[user_id]
                
            except ValueError:
                bot.reply_to(message, TEXTS[user_lang]['invalid_deposit'])
                
    except Exception as e:
        logger.error(f"Ошибка при создании аккаунта: {e}", exc_info=True)
        bot.reply_to(message, TEXTS[user_lang].get('error_creating_account', 'Error occurred while creating account'))
        del user_states[user_id]


# def user_message_handler(message):
#     if not message.reply_to_message.text.startswith('Config'):
#         bot_chat_user(message, bot)
#     elif message.reply_to_message.text.startswith('Config'):
#         if message.reply_to_message.text.split('_')[1] == "key":
#             user_settings = bits_user_settings.find_one({'user_id': message.from_user.id})
#             user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
#             if not hasattr(bot, 'user_states'):
#                 bot.user_states = {}
            
#             bot.user_states[message.from_user.id] = {
#                 'step': 'key',
#                 'user_id': message.from_user.id
#             }
            
#             # Вызываем handle_new_connection из bits_status
#             handle_new_connection(
#                 message=message,
#                 bot=bot,
#                 state=bot.user_states[message.from_user.id],
#                 lang=user_lang,
#                 user_id=message.from_user.id
#             )
#             return
#         elif message.reply_to_message.text.split('_')[1] == "secret":
#             user_settings = bits_user_settings.find_one({'user_id': message.from_user.id})
#             user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
#             if not hasattr(bot, 'user_states'):
#                 bot.user_states = {}
            
#             bot.user_states[message.from_user.id] = {
#                 'step': 'secret',
#                 'user_id': message.from_user.id
#             }
#         elif message.reply_to_message.text.split('_')[1] == "deposit":
#             user_settings = bits_user_settings.find_one({'user_id': message.from_user.id})
#             user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
#             if not hasattr(bot, 'user_states'):
#                 bot.user_states = {}
            
#             bot.user_states[message.from_user.id] = {
#                 'step': 'deposit',
#                 'user_id': message.from_user.id
#             }
#         else:
#             return bot.reply_to(message, "Config_error:")
        
#         handle_new_connection(
#             message=message,
#             bot=bot,
#             state=bot.user_states[message.from_user.id],
#             lang=user_lang,
#             user_id=message.from_user.id
#         )
#         return

@bot.message_handler(func=lambda message: message.chat.id == SUPPORT_GROUP_ID and message.reply_to_message)
def support_reply_handler(message):
    handle_support_reply(message, bot)

# Обработчик редактирования сообщений
@bot.edited_message_handler(func=lambda message: message.chat.id != SUPPORT_GROUP_ID)
def on_edit(message):
    handle_edited_message(message, bot)

# Обработчик удаления сообщений
@bot.message_handler(content_types=['delete_chat_message'])
def on_delete(message):
    handle_deleted_message(message, bot)

def main():
    try:
        # Устанавливаем команды меню при запуске бота
        setup_bot_commands()
        print("Бот запущен...")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {str(e)}")

if __name__ == "__main__":
    main()

