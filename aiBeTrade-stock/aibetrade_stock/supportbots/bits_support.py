import telebot
from telebot import types
from datetime import datetime
from pymongo import MongoClient
import os
import langdetect
from bits_info import create_info_menu, get_info_texts, handle_info_section
from bits_chat_helping import bot_chat_user, handle_support_reply, SUPPORT_GROUP_ID, handle_edited_message, handle_deleted_message
from bits_statistics import get_statistics, create_statistics_menu, create_robots_menu, format_robot_stats,get_statistics_system
import logging

logger = logging.getLogger('BitsBot')

# Укажите токен вашего бота
# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
client = MongoClient(mongo_url)
db = client["nntcapital"]
bits_settings = db["bits_settings"]
bits_user_settings = db["bits_user_settings"]

# Хранит состояние выбранного раздела и текст сообщения
user_state = {}

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
        types.InlineKeyboardButton("🇺🇸 English", callback_data="en"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
        types.InlineKeyboardButton("🇫🇷 Français", callback_data="fr"),
        types.InlineKeyboardButton("🇩🇪 Deutsch", callback_data="de"),
        types.InlineKeyboardButton("🇪🇸 Español", callback_data="es"),
        types.InlineKeyboardButton("🇨🇳 中文", callback_data="zh")
    ]
    markup.add(*buttons)
    return markup
# Функция для создания inline-кнопок главного меню с учетом языка
def create_main_menu(lang='en'):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    menu_buttons = {
        'ru': [
            ("🛠️ Команды", "help"),
            ("ℹ️ Информация", "info"),
            ("🔔 Статистика", "status"),
            ("🌐 Язык", "lang")
        ],
        'en': [
            ("🛠️ Commands", "help"),
            ("ℹ️ Information", "info"),
            ("🔔 Status", "status"),
            ("🌐 Language", "lang")
        ],
        'fr': [
            ("🛠️ Befehle", "help"),
            ("ℹ️ Information", "info"),
            ("🔔 Statistiques", "status"),
            ("🌐 Langue", "lang")
        ],
        'de': [
            ("🛠️ Befehle", "help"),
            ("ℹ️ Information", "info"),
            ("🔔 Statistiken", "status"),
            ("🌐 Sprache", "lang")
        ],
        'es': [
            ("🛠️ Comandos", "help"),
            ("ℹ️ Información", "info"),
            ("🔔 Estadísticas", "status"),
            ("🌐 Idioma", "lang")
        ],
        'zh': [
            ("🛠️ 命令", "help"),
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

# Устовка команд меню бота
def setup_bot_commands(lang='en'):
    try:
        user_id = bits_user_settings.find_one({'user_id': bot.message.from_user.id})
        lang = user_id.get('lang_set', 'en') if user_id else 'en'
        logger.info(f"Кода выбрали команду setup_bot_commands {lang} для пользователя {bot.message.from_user.id}")
        # Команды для разных языков
        commands = {
            "ru": [
                telebot.types.BotCommand("start", "Запустить бота"),
                telebot.types.BotCommand("help", "Команды"),
                telebot.types.BotCommand("language", "Выбор языка"),
                telebot.types.BotCommand("status", "Статус сервисов"),
                telebot.types.BotCommand("info", "Информация о боте")
            ],
            "en": [
                telebot.types.BotCommand("start", "Start the bot"),
                telebot.types.BotCommand("help", "Commands"),
                telebot.types.BotCommand("language", "Choose language"),
                telebot.types.BotCommand("status", "Service status"),
                telebot.types.BotCommand("info", "Information")
            ],
            "fr": [
                telebot.types.BotCommand("start", "Démarrer le bot"),
                telebot.types.BotCommand("help", "Commandes"),
                telebot.types.BotCommand("language", "Choisir la langue"),
                telebot.types.BotCommand("status", "État des services"),
                telebot.types.BotCommand("info", "Information")
            ],
            "de": [
                telebot.types.BotCommand("start", "Bot starten"),
                telebot.types.BotCommand("help", "Befehle"),
                telebot.types.BotCommand("language", "Sprache wählen"),
                telebot.types.BotCommand("status", "Servicestatus"),
                telebot.types.BotCommand("info", "Bot-Information")
            ],
            "es": [
                telebot.types.BotCommand("start", "Iniciar el bot"),
                telebot.types.BotCommand("help", "Comandos"),
                telebot.types.BotCommand("language", "Elegir idioma"),
                telebot.types.BotCommand("status", "Estado del servicio"),
                telebot.types.BotCommand("info", "Información del bot")
            ],
            "zh": [
                telebot.types.BotCommand("start", "启动机器人"),
                telebot.types.BotCommand("help", "命令"),
                telebot.types.BotCommand("language", "选择语言"),
                telebot.types.BotCommand("status", "服务状态"),
                telebot.types.BotCommand("info", "机器人信息")
            ]
        }
        
        # Устанавливаем команды для каждого языка
        bot.set_my_commands(commands[lang], language_code=lang)
        
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
    logger.info(f"Кода выбрали команду help: {user_settings} {message.from_user.id} {user_lang}")
    
    help_texts = {
        'ru': """
🤖 Доступные команды:
/start - Запустить бота
/help - Показать это сообщение
/language - Выбрать язык
/status - Статус сервисов
/info - Информация о боте
""",
        'fr': """
🤖 Commandes disponibles:
/start - Démarrer le bot
/help - Afficher ce message
/language - Choisir la langue
/status - État des services
/info - Information sur le bot
""",
        'de': """
🤖 Verfügbare Befehle:
/start - Bot starten
/help - Diese Nachricht anzeigen
/language - Sprache wählen
/status - Servicestatus
/info - Bot-Information
""",
        'es': """
🤖 Comandos disponibles:
/start - Iniciar el bot
/help - Mostrar este mensaje
/language - Elegir idioma
/status - Estado del servicio
/info - Información del bot
""",
        'zh': """
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
def handle_status(message):
    user_id = message.chat.id
    logger.info(f"message.from_user.id: {message.from_user.id}")
    logger.info(f"message.chat.id: {message.chat.id}")
    
    user_settings = bits_user_settings.find_one({'user_id': user_id})
    user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
    logger.info(f"User language кода вызвали команду status: {user_id} {user_lang}")
    status_texts = {
        'ru': "🔄 Проверка статуса сервисов...",
        'fr': "🔄 Vérification de l'état des services...",
        'de': "🔄 Überprüfung des Servicestatus...",
        'es': "🔄 Comprobando el estado del servicio...",
        'en': "🔄 Checking service status..."
    }
    
    bot.send_message(message.chat.id, status_texts.get(user_lang, status_texts['en']))
    
    status_texts = get_statistics(bot,message.chat.id,message.message_id,user_lang)
    
    # menu_texts = {
    #     'ru': "Выберите нужное действие:",
    #     'en': "Please select an action:",
    #     'fr': "Veuillez sélectionner une action:",
    #     'de': "Bitte wählen Sie eine Aktion:",
    #     'es': "Por favor, seleccione una acción:",
    #     'zh': "请选择操作："
    # }
    
    # # Отправляем приветствие и меню на языке пользователя
    # bot.send_message(
    #     message.chat.id,
    #     f"{menu_texts.get(user_lang, menu_texts['en'])}",
    #     reply_markup=create_main_menu(user_lang)
    # )

@bot.message_handler(commands=['info'])
def handle_info(message):
    user_settings = bits_user_settings.find_one({'user_id': message.from_user.id})
    user_lang = user_settings.get('lang_set', 'en') if user_settings else 'en'
    
    info_texts = {
        'ru': "ℹ️ Информация о боте и его возможностях",
        'fr': "ℹ️ Informations sur le bot et ses capacités",
        'de': "ℹ️ Informationen über den Bot und seine Fähigkeiten",
        'es': "ℹ️ Información sobre el bot y sus capacidades",
        'zh': "ℹ️ 关于机器人及其功能的信息",
        'en': "ℹ️ Information about the bot and its capabilities"
    }
    bot.send_message(message.chat.id, info_texts.get(user_lang, info_texts['en']))

    # Получаем тексты ля текущго языка
    texts = get_info_texts(user_lang)
    
    # Отправляем заголовок информационного меню с кнопками
    bot.send_message(
        message.chat.id,
        texts['menu_title'],
        reply_markup=create_info_menu(user_lang),
        parse_mode='HTML'
    )

def welcome_text_lang(lang):
    welcome_texts = {
        'ru': (
            "Привет, мой друг! 👋\n\n"
            "Я твой персональный помощник в мире трейдинга. "
            "Я помогу тебе отслеживать сигналы, управлять портфелем "
            "и быть в курсе всех важных событий на рынке.\n\n"
            "Если у тебя возникнут вопросы, просто отправь сообщение в этом же чате.\n\n"
        ),
        'zh': (
            "你好，我的朋友！👋\n\n"
            "我是你的个人交易助理。我将帮助你跟踪信号、管理你的投资组合，并随时了解所有重要的市场事件。\n\n"
            "如果遇到问题，请直接在聊天中发送 /help 消息，我会帮助你。\n\n"
        ),
        'fr': (
            "Bonjour, mon ami! 👋\n\n"
            "Je suis votre assistant de trading personnel. Je vous aidera à suivre les signaux, "
            "gérer votre portefeuille et rester à jour avec tous les événements importants du marché.\n\n"
            "Si vous avez des questions, envoyez simplement un message dans ce même chat.\n\n"
        ),
        'de': (
            "Hallo, mein Freund! 👋\n\n"
            "Ich bin Ihr persönlicher Handelsassistent. Ich werde Ihnen helfen, die Signale zu verfolgen, "
            "Ihr Portfolio zu verwalten und stets über alle wichtigen Marktveranstaltungen auf dem Laufenden zu bleiben.\n\n"
            "Wenn Sie Fragen haben, senden Sie einfach eine Nachricht in diesem gleichen Chat.\n\n"
        ),
        'es': (
            "¡Hola, mi amigo! 👋\n\n"
            "Soy tu asistente de trading personal. Te ayudaré a seguir las señales, "
            "gestionar tu cartera y mantenerte al margen de todos los eventos importantes del mercado.\n\n"
            "Si tienes alguna pregunta, simplemente envía un mensaje en este mismo chat.\n\n"
        ),
        'en': (
            "Hello, my friend! 👋\n\n"
            "I'm your personal trading assistant. "
            "I'll help you track signals, manage your portfolio, "
            "and stay updated with all important market events.\n\n"
            "If you have any questions, simply send a message in this same chat.\n\n"
        )
    }
    return welcome_texts.get(lang, welcome_texts['en'])

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        # Проверяем, есть ли пльзователь в базе
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
                'fr': "Veuillez sélectionner une action:",
                'de': "Bitte wählen Sie eine Aktion:",
                'es': "Por favor, seleccione una acción:",
                'zh': "请选择操作："
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

        # Обработка статистики
        if call.data.startswith('stats_') or call.data.startswith('robot_'):
            if call.data == 'stats_trading':
                # Показываем торговый результат
                get_statistics_system(bot, call.message.chat.id,call.message.message_id, user_lang)
                
            elif call.data == 'stats_robots':
                # Получаем список никнеймов
                nicknames = db["bits_user_trade"].distinct("nickname")
                markup = create_robots_menu(nicknames, user_lang)
                
                # Отправляем меню с роботами
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
                )
                
            elif call.data.startswith('robot_'):
                # Получаем данные конкретного робота
                nickname = call.data.replace('robot_', '')
                robot_data = db["bits_user_trade"].find({"nickname": nickname})
                
                if robot_data:
                    # Форматируем и отправляем данные
                    stats_text = format_robot_stats(robot_data, user_lang)
                    markup = create_statistics_menu(bot, call.message.chat.id, user_lang)
                    
                    bot.edit_message_text(
                        stats_text,
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=markup,
                        parse_mode='HTML'
                    )
                    
            elif call.data == 'stats_back':
                # Возвращаемся в главное меню
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=create_main_menu(user_lang)
                )
                
            elif call.data == 'stats_menu':
                # Возвращаемся в меню статистики
                markup = create_statistics_menu(bot, call.message.chat.id, user_lang)
                bot.edit_message_reply_markup(
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
                )

        # Обработка информационного меню
        elif call.data == "info":
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
        elif call.data in ["ru", "en", "fr", "de", "es", "zh"]:
            # Маппинг кодов языков из кнопок в коды для системы
            lang_mapping = {
                "ru": "ru",
                "en": "en",
                "fr": "fr",
                "de": "de",
                "es": "es",
                "zh": "zh"
            }
            selected_lang = lang_mapping[call.data]
            setup_bot_commands(selected_lang)
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
                'fr': "✅ Langue changée avec succès en Français",
                'de': "✅ Sprache erfolgreich auf Deutsch geändert",
                'es': "✅ Idioma cambiado exitosamente a Español",
                'zh': "✅ 语言已成功更改为中文"
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
                'fr': "Veuillez sélectionner une action:",
                'de': "Bitte wählen Sie eine Aktion:",
                'es': "Por favor, seleccione una acción:",
                'zh': "请选择操作："
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
                handle_status(call.message)
            elif call.data == "lang":
                # Показываем меню выбора языка
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="🌐 Select language / Выберите язык / Choisissez la langue / Wählen Sie die Sprache / Seleccione el idioma / 选择语言",
                    reply_markup=create_lang_menu()
                )
                
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        bot.answer_callback_query(call.id, "An error occurred. Please try again.")

@bot.message_handler(func=lambda message: message.chat.id != SUPPORT_GROUP_ID and not message.text.startswith('/'))
def user_message_handler(message):
    bot_chat_user(message, bot)

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

