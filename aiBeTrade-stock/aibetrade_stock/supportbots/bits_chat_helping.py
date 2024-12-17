from telebot import TeleBot, apihelper
from telebot.types import Message, ForumTopic
import time
import logging
import sys
import os
import re
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests
from cachetools import TTLCache, LRUCache

# Настройка логирования с добавлением метрик производительности
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(performance_metrics)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BitsBot')

# Добавляем фильтр для метрик производительности
class PerformanceMetricsFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'performance_metrics'):
            record.performance_metrics = ''
        return True

logger.addFilter(PerformanceMetricsFilter())

# ID группы поддержки
SUPPORT_GROUP_ID = -1002366409050

# Константы для кэширования и производительности
CACHE_TIMEOUT = 300  # 5 минут
MESSAGE_BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 5

# Подключение к MongoDB с пулом соединений
MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,
    waitQueueTimeoutMS=2500,
    connectTimeoutMS=2000,
    serverSelectionTimeoutMS=3000,
    retryWrites=True
)
db = client.nntcapital

# Кэш для тем и сообщений
topic_cache = TTLCache(maxsize=1000, ttl=CACHE_TIMEOUT)
message_cache = LRUCache(maxsize=5000)

def create_session_with_retry():
    """
    Создает сессию с улучшенными настройками повторных попыток
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Улучшенные настройки таймаутов
apihelper.SESSION = create_session_with_retry()
apihelper.READ_TIMEOUT = 60
apihelper.CONNECT_TIMEOUT = 20

def init_bot(token: str) -> TeleBot:
    """
    Инициализация бота с улучшенными настройками
    """
    bot = TeleBot(token)
    bot.threaded = True
    bot.worker_pool = 16
    return bot

def run_bot(bot: TeleBot):
    """
    Запуск бота с улучшенной обработкой ошибок
    """
    retry_count = 0
    while True:
        try:
            logger.info("Запуск бота...")
            bot.infinity_polling(timeout=90, long_polling_timeout=60)
            retry_count = 0
        except requests.exceptions.ReadTimeout:
            retry_count += 1
            wait_time = min(30, retry_count * RETRY_DELAY)
            logger.warning(f"Таймаут соединения, ожидание {wait_time} секунд перед перезапуском...")
            time.sleep(wait_time)
        except Exception as e:
            retry_count += 1
            wait_time = min(60, retry_count * RETRY_DELAY)
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            time.sleep(wait_time)

def init_db():
    """
    Инициализация базы данных
    """
    try:
        # Создаем коллекцию для тем поддержки если её нет
        if 'bits_user_help' not in db.list_collection_names():
            db.create_collection('bits_user_help')
        
        # Создаем индексы
        db.bits_user_help.create_index([('user_id', ASCENDING)])
        db.bits_user_help.create_index([('topic_id', ASCENDING)])
        db.bits_user_help.create_index([('username', ASCENDING)])
        
        # Создаем коллекцию для истории сообщений
        if 'bits_support_messages' not in db.list_collection_names():
            db.create_collection('bits_support_messages')
        
        db.bits_support_messages.create_index([('topic_id', ASCENDING)])
        db.bits_support_messages.create_index([('created_at', ASCENDING)])
        
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}", exc_info=True)

def get_topic_from_db(user_id: int) -> dict:
    """
    Получает информацию о теме из базы данных
    """
    try:
        return db.bits_user_help.find_one(
            {'user_id': user_id},
            sort=[('last_message_at', -1)]
        )
    except Exception as e:
        logger.error(f"Ошибка при получении темы из БД: {e}", exc_info=True)
        return None

def save_topic_to_db(user_id: int, topic_id: int, username: str):
    """
    Сохраняет информацию о теме в базу данных
    """
    try:
        db.bits_user_help.insert_one({
            'user_id': user_id,
            'topic_id': topic_id,
            'username': username,
            'created_at': datetime.utcnow(),
            'last_message_at': datetime.utcnow()
        })
        logger.info(f"Сохранено соответствие: user_id={user_id}, topic_id={topic_id}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}", exc_info=True)

def update_last_message_time(topic_id: int):
    """
    Обновляет время последнего сообщения в теме
    """
    try:
        db.bits_user_help.update_one(
            {'topic_id': topic_id},
            {'$set': {'last_message_at': datetime.utcnow()}}
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени: {e}", exc_info=True)

def save_message_to_db(topic_id: int, user_id: int, message_text: str, message_id: int, support_message_id: int = None, is_support: bool = False):
    """
    Сохраняет сообщение в историю с оптимизированной производительностью
    """
    start_time = time.time()
    try:
        # Проверяем кэш
        cache_key = f"{topic_id}_{message_id}"
        if cache_key in message_cache:
            return message_cache[cache_key]

        # Подготовка данных
        message_data = {
            "topic_id": topic_id,
            "user_id": user_id,
            "message_text": message_text,
            "message_id": message_id,
            "support_message_id": support_message_id,
            "is_support": is_support,
            "created_at": datetime.utcnow()
        }

        # Пакетная вставка
        result = db.bits_support_messages.insert_one(message_data)
        
        # Кэшируем результат
        message_cache[cache_key] = result.inserted_id
        
        # Очистка старых сообщений
        if message_id % 100 == 0:  # Периодическая очистка
            db.bits_support_messages.delete_many({
                "created_at": {"$lt": datetime.utcnow() - timedelta(days=30)}
            })

        execution_time = time.time() - start_time
        logger.info(
            f"Сообщение сохранено",
            extra={"performance_metrics": f"execution_time={execution_time:.2f}s"}
        )
        return result.inserted_id

    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения: {e}", exc_info=True)
        return None

def check_topic_exists(bot: TeleBot, topic_id: int) -> bool:
    """
    Проверяет существование темы в группе
    """
    try:
        # Пытаемся отправить пустое сообщение в тему
        bot.send_chat_action(SUPPORT_GROUP_ID, 'typing', message_thread_id=topic_id)
        return True
    except Exception as e:
        logger.warning(f"Тема {topic_id} не существует: {e}")
        return False

def delete_topic_from_db(topic_id: int):
    """
    Удаляет тему из базы данных
    """
    try:
        db.bits_user_help.delete_one({'topic_id': topic_id})
        logger.info(f"Тема {topic_id} удалена из БД")
    except Exception as e:
        logger.error(f"Ошибка при удалении темы из БД: {e}", exc_info=True)

def get_or_create_topic(bot: TeleBot, username: str, user_id: int) -> int:
    """
    Получает существующую или создает новую тему для пользователя
    Возвращает topic_id или None в случае ошибки
    """
    try:
        # Проверяем существующую тему
        existing_topic = db.bits_user_help.find_one({'user_id': user_id})
        if existing_topic:
            # Проверяем существование темы в группе
            if check_topic_exists(bot, existing_topic['topic_id']):
                return existing_topic['topic_id']
            else:
                # Если тема не существует, удаляем запись
                db.bits_user_help.delete_one({'user_id': user_id})

        # Создаем новую тему
        try:
            topic_name = f"Support chat with {username}"
            new_topic = bot.create_forum_topic(
                SUPPORT_GROUP_ID,
                topic_name
            )
            
            # Сохраняем информацию о теме
            topic_id = new_topic.message_thread_id
            save_topic_to_db(user_id, topic_id, username)
            
            # Отправляем приветственное сообщение
            bot.send_message(
                SUPPORT_GROUP_ID,
                f"Начат новый чат поддержки с пользователем {username} (ID: {user_id})",
                message_thread_id=topic_id
            )
            
            return topic_id

        except Exception as e:
            logger.error(f"Ошибка при создании темы: {e}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"Ошибка в get_or_create_topic: {e}", exc_info=True)
        return None

def get_user_topic_id(user_id: int) -> int:
    """
    Получает ID темы по ID пользователя
    """
    try:
        topic_data = db.bits_user_help.find_one(
            {'user_id': user_id},
            sort=[('last_message_at', -1)]
        )
        return topic_data['topic_id'] if topic_data else None
    except Exception as e:
        logger.error(f"Ошибка при получении темы: {e}", exc_info=True)
        return None

def get_support_message_id(topic_id: int, user_message_id: int) -> int:
    """
    Получает ID сообщения в группе поддержки по ID оригинального сообщения
    """
    try:
        message = db.bits_support_messages.find_one({
            'topic_id': topic_id,
            'message_id': user_message_id
        })
        return message.get('support_message_id') if message else None
    except Exception as e:
        logger.error(f"Ошибка при получении ID сообщения: {e}", exc_info=True)
        return None

def update_message_in_db(topic_id: int, message_id: int, new_text: str = None, is_deleted: bool = False):
    """
    Обновляет сообщение в базе данных
    """
    try:
        update_data = {
            'is_edited': True if new_text else False,
            'is_deleted': is_deleted
        }
        if new_text:
            update_data['message'] = new_text

        db.bits_support_messages.update_one(
            {'topic_id': topic_id, 'message_id': message_id},
            {'$set': update_data}
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении сообщения: {e}", exc_info=True)

def handle_edited_message(message: Message, bot: TeleBot):
    """
    Обработка отредактированных сообщений
    """
    try:
        user_id = message.from_user.id
        topic = get_topic_from_db(user_id)
        
        if not topic:
            logger.warning(f"Н найдена тема для пользователя {user_id}")
            return
            
        topic_id = topic['topic_id']
        
        # Обновляем сообщение в базе
        update_message_in_db(topic_id, message.message_id, message.text)
        
        try:
            # Отправляем уведомление в группу поддержки
            bot.send_message(
                SUPPORT_GROUP_ID,
                f"⚠️ Пользователь отредактировал сообщение:\n{message.text}",
                message_thread_id=topic_id
            )
            logger.info(f"Обработано редактирование сообщения от пользователя {user_id}")
        except Exception as e:
            error_msg = str(e).lower()
            if "forbidden: bot was blocked by the user" in error_msg:
                logger.warning(f"Бот заблокирован пользователем {user_id}")
            elif "bot can't initiate conversation with a user" in error_msg:
                logger.warning(f"Пользователь {user_id} не инициировал диалог с ботом")
            else:
                logger.error(f"Ошибка при отправке уведомления об редактировании: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке редактирования: {e}", exc_info=True)

def handle_deleted_message(message: Message, bot: TeleBot):
    """
    Обработка удаленных сообщений
    """
    try:
        user_id = message.from_user.id
        topic = get_topic_from_db(user_id)
        
        if not topic:
            logger.warning(f"Не найдена тема для пользователя {user_id}")
            return
            
        topic_id = topic['topic_id']
        
        # Обновляем статус сообщения в базе
        update_message_in_db(topic_id, message.message_id, is_deleted=True)
        
        try:
            # Отправляем уведомление в группу поддержки
            bot.send_message(
                SUPPORT_GROUP_ID,
                "🗑 Пользователь удалил сообщение",
                message_thread_id=topic_id
            )
            logger.info(f"Обработано удаление сообщения от пользователя {user_id}")
        except Exception as e:
            error_msg = str(e).lower()
            if "forbidden: bot was blocked by the user" in error_msg:
                logger.warning(f"Бот заблокирован пользователем {user_id}")
            elif "bot can't initiate conversation with a user" in error_msg:
                logger.warning(f"Пользователь {user_id} не инициировал диалог с ботом")
            else:
                logger.error(f"Ошибка при отправке уведомления об удалении: {e}", exc_info=True)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке удаления: {e}", exc_info=True)

def bot_chat_user(message: Message, bot: TeleBot):
    """
    Оптимизированная обработка сообщений пользователя
    """
    try:
        # Получаем или создаем тему для пользователя
        topic_id = get_or_create_topic(bot, message.from_user.username or str(message.from_user.id), message.from_user.id)
        if not topic_id:
            logger.error("Не удалось создать тему")
            bot.reply_to(message, "Произошла ошибка при создании темы. Попробуйте позже.")
            return

        # Пересылаем сообщение в группу поддержки
        try:
            forwarded = bot.forward_message(
                SUPPORT_GROUP_ID,
                message.chat.id,
                message.message_id,
                message_thread_id=topic_id
            )

            # Сохраняем сообщение в базу данных
            save_message_to_db(
                topic_id,
                message.from_user.id,
                message.text or message.caption or "",
                message.message_id,
                forwarded.message_id
            )

            # Обновляем время последнего сообщения
            update_last_message_time(topic_id)

            # Устанавливаем иконку "новое сообщение"
            success = update_topic_icon(bot, topic_id, 'new')
            if not success:
                logger.warning(f"Не удалось обновить иконку темы {topic_id}")

        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {e}", exc_info=True)
            bot.reply_to(message, "Произошла ошибка при обработке сообщения. Попробуйте позже.")

    except Exception as e:
        logger.error(f"Ошибка в bot_chat_user: {e}", exc_info=True)
        bot.reply_to(message, "Произошла ошибка при обработке сообщения. Попробуйте позже.")

def handle_support_reply(message: Message, bot: TeleBot):
    """
    Обработка ответов из группы поддержки.
    Сообщение отправляется пользователю только если это ответ на его сообщение.
    """
    try:
        # Проверяем, что это сообщение из группы поддержки
        if message.chat.id != SUPPORT_GROUP_ID:
            return

        # Проверяем, что это ответ на сообщение
        if not message.reply_to_message:
            return

        topic_id = message.message_thread_id
        if not topic_id:
            return

        # Получаем информацию о пересылке
        forward_from = message.reply_to_message.forward_from
        forward_sender_name = getattr(message.reply_to_message, 'forward_sender_name', None)
        forward_from_chat = message.reply_to_message.forward_from_chat
        
        logger.info(f"Информация о пересылке: from={forward_from}, sender_name={forward_sender_name}, chat={forward_from_chat}")

        # Проверяем, что отвечают на пересланное сообщение от пользователя
        is_forwarded_message = (
            forward_from is not None or  # Обычный случай
            forward_sender_name is not None or  # Пользователь скрыл свой профиль
            (forward_from_chat is not None and forward_from_chat.type == 'private')  # Сообщение переслано из приватного чата
        )
        
        if not is_forwarded_message:
            # Это внутреннее обсуждение в группе поддержки
            logger.info(f"Внутреннее обсуждение в теме {topic_id}, сообщение не будет отправлено пользователю")
            return

        # Получаем информацию о пользователе из кэша или БД
        user_data = db.bits_user_help.find_one({'topic_id': topic_id})
        if not user_data:
            logger.error(f"Не найдена информация о пользователе для темы {topic_id}")
            return

        try:
            # Сначала устанавливаем иконку "отвечено" и убираем "новое сообщение"
            success = update_topic_icon(bot, topic_id, 'answered')
            if not success:
                logger.warning(f"Не удалось обновить иконку темы {topic_id}")
            
            # Даем время на обработку изменения иконки
            time.sleep(0.5)

            # Отправляем ответ пользователю
            sent_message = bot.send_message(
                user_data['user_id'],
                message.text or message.caption or "",
                reply_to_message_id=message.reply_to_message.forward_from_message_id if message.reply_to_message.forward_from_message_id else None
            )

            # Сохраняем ответ в базу данных
            save_message_to_db(
                topic_id,
                user_data['user_id'],
                message.text or message.caption or "",
                sent_message.message_id,
                message.message_id,
                is_support=True
            )

            # Обновляем время последнего сообщения
            update_last_message_time(topic_id)

            logger.info(f"Ответ отправлен пользователю {user_data['user_id']} в теме {topic_id}")

        except Exception as e:
            logger.error(f"Ошибка при отправке ответа пользователю: {e}", exc_info=True)
            bot.reply_to(message, "Ошибка при отправке сообщения пользователю. Возможно, пользователь заблокировал бота.")

    except Exception as e:
        logger.error(f"Общая ошибка в handle_support_reply: {e}", exc_info=True)
        bot.reply_to(message, "Произошла ошибка при обработке ответа")

def handle_user_message(message: Message, bot: TeleBot):
    """
    Обработка сообщений от пользователей
    """
    try:
        # Получаем тему пользователя
        topic_id = get_user_topic_id(message.from_user.id)
        if not topic_id:
            # Если темы нет, создаем новую
            topic_id = get_or_create_topic(bot, message.from_user.username, message.from_user.id)
            if not topic_id:
                logger.error("Не удалось создать тему для пользователя")
                return

        try:
            # Пересылаем сообщение в группу поддержки
            forwarded = bot.forward_message(
                chat_id=SUPPORT_GROUP_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                message_thread_id=topic_id
            )

            # Сохраняем сообщение в базу данных
            save_message_to_db(
                topic_id,
                message.from_user.id,
                message.text or message.caption or "",
                message.message_id,
                forwarded.message_id
            )

            # Обновляем время последнего сообщения
            update_last_message_time(topic_id)

            # Устанавливаем иконку "требует внимания"
            success = update_topic_icon(bot, topic_id, 'attention')
            if not success:
                logger.warning(f"Не удалось обновить иконку темы {topic_id}")

        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {e}", exc_info=True)
            bot.reply_to(message, "Произошла ошибка при обработке вашего сообщения")

    except Exception as e:
        logger.error(f"Общая ошибка в handle_user_message: {e}", exc_info=True)
        bot.reply_to(message, "Произошла ошибка при обработке вашего сообщения")

# Иконки для тем
TOPIC_ICONS = {
    'new': '‼️',           # Новая тема
    'answered': 'ok',      # Ответ получен
    'attention': '‼️',     # Требует внимания
}

def update_topic_icon(bot: TeleBot, topic_id: int, icon_type: str):
    """
    Обновляет иконку темы в группе поддержки
    Args:
        bot: Экземпляр бота
        topic_id: ID темы
        icon_type: Тип иконки ('new', 'answered', 'attention')
    """
    try:
        if icon_type not in TOPIC_ICONS:
            logger.error(f"Неизвестный тип иконки: {icon_type}")
            return False
            
        # Получаем информацию о теме из нашей БД
        topic_data = db.bits_user_help.find_one({'topic_id': topic_id})
        if not topic_data:
            logger.error(f"Тема {topic_id} не найдена в БД")
            return False
            
        # Формируем новое название темы
        username = topic_data.get('username', 'Unknown')
        icon = TOPIC_ICONS[icon_type]
        new_name = f"{icon} {username}"
        
        try:
            # Обновляем название темы
            bot.edit_forum_topic(
                chat_id=SUPPORT_GROUP_ID,
                message_thread_id=topic_id,
                name=new_name
            )
            logger.info(f"Успешно обновлена иконка темы {topic_id} на {icon_type}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении названия темы: {e}", exc_info=True)
            return False
            
    except Exception as e:
        logger.error(f"Общая ошибка в update_topic_icon: {e}", exc_info=True)
        return False

# Инициализируем БД при запуске
init_db()
