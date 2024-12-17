from telebot import TeleBot
from telebot.types import Message, ForumTopic
import time
import logging
import sys
import os
import re
from pymongo import MongoClient, ASCENDING
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import requests
from telebot import apihelper
from cachetools import TTLCache, LRUCache

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('NfterriumBot')

# ID группы поддержки
SUPPORT_GROUP_ID = -1002413043733

# Иконки для тем
TOPIC_ICONS = {
    'new': '‼️',           # Новая тема
    'answered': 'ok',      # Ответ получен
    'attention': '‼️',     # Требует внимания
}

# Настройка кэширования
topic_cache = TTLCache(maxsize=100, ttl=300)  # Кэш на 5 минут
message_cache = LRUCache(maxsize=1000)  # Кэш для сообщений

# Подключение к MongoDB с оптимизированными настройками
MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=45000,
    waitQueueTimeoutMS=5000
)
db = client.nntcapital

def create_session_with_retry():
    """
    Создает сессию с настройками повторных попыток
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # количество повторных попыток
        backoff_factor=1,  # фактор задержки между попытками
        status_forcelist=[429, 500, 502, 503, 504]  # коды ошибок для повторных попыток
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

apihelper.SESSION = create_session_with_retry()
apihelper.READ_TIMEOUT = 30
apihelper.CONNECT_TIMEOUT = 10

def init_bot(token: str) -> TeleBot:
    """
    Инициализация бота с настройками таймаутов
    """
    bot = TeleBot(token)
    bot.threaded = False  # Отключаем многопоточность для лучшего контроля
    return bot

def init_db():
    """
    Инициализация базы данных
    """
    try:
        # Создаем коллекцию для тем поддержки если её нет
        if 'nfterrium_user_help' not in db.list_collection_names():
            db.create_collection('nfterrium_user_help')
        
        # Создаем индексы
        db.nfterrium_user_help.create_index([('user_id', ASCENDING)])
        db.nfterrium_user_help.create_index([('topic_id', ASCENDING)])
        db.nfterrium_user_help.create_index([('username', ASCENDING)])
        
        # Создаем коллекцию для истории сообщений
        if 'nfterrium_support_messages' not in db.list_collection_names():
            db.create_collection('nfterrium_support_messages')
        
        db.nfterrium_support_messages.create_index([('topic_id', ASCENDING)])
        db.nfterrium_support_messages.create_index([('created_at', ASCENDING)])
        
        logger.info("База данных инициализирована успешно")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}", exc_info=True)

def get_topic_from_db(user_id: int) -> dict:
    """
    Получает информацию о теме из базы данных с использованием кэша
    """
    try:
        # Проверяем кэш
        cache_key = f"topic_{user_id}"
        if cache_key in topic_cache:
            return topic_cache[cache_key]
        
        # Если нет в кэше, получаем из БД
        topic = db.nfterrium_user_help.find_one(
            {'user_id': user_id},
            sort=[('last_message_at', -1)]
        )
        
        if topic:
            topic_cache[cache_key] = topic
        return topic
    except Exception as e:
        logger.error(f"Ошибка при получении темы из БД: {e}", exc_info=True)
        return None

def save_topic_to_db(user_id: int, topic_id: int, username: str):
    """
    Сохраняет информацию о теме в базу данных и кэш
    """
    try:
        data = {
            'user_id': user_id,
            'topic_id': topic_id,
            'username': username,
            'created_at': datetime.utcnow(),
            'last_message_at': datetime.utcnow()
        }
        db.nfterrium_user_help.insert_one(data)
        
        # Обновляем кэш
        cache_key = f"topic_{user_id}"
        topic_cache[cache_key] = data
        
        logger.info(f"Сохранено соответствие: user_id={user_id}, topic_id={topic_id}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении в БД: {e}", exc_info=True)

def update_last_message_time(topic_id: int):
    """
    Обновляет время последнего сообщения в теме
    """
    try:
        current_time = datetime.utcnow()
        db.nfterrium_user_help.update_one(
            {'topic_id': topic_id},
            {'$set': {'last_message_at': current_time}}
        )
        
        # Обновляем кэш если есть
        for key, value in topic_cache.items():
            if value and value.get('topic_id') == topic_id:
                value['last_message_at'] = current_time
                break
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени: {e}", exc_info=True)

def save_message_to_db(topic_id: int, user_id: int, message_text: str, message_id: int, support_message_id: int = None, is_support: bool = False):
    """
    Сохраняет сообщение в историю с кэшированием
    """
    try:
        message_data = {
            'topic_id': topic_id,
            'user_id': user_id,
            'message': message_text,
            'message_id': message_id,
            'is_support': is_support,
            'created_at': datetime.utcnow(),
            'is_edited': False,
            'is_deleted': False
        }
        
        if support_message_id:
            message_data['support_message_id'] = support_message_id
        
        # Сохраняем в БД
        result = db.nfterrium_support_messages.insert_one(message_data)
        
        # Кэшируем сообщение
        cache_key = f"msg_{topic_id}_{message_id}"
        message_cache[cache_key] = message_data
        
        logger.info(f"Сообщение сохранено в БД: topic_id={topic_id}, message_id={message_id}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении сообщения: {e}", exc_info=True)

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
        db.nfterrium_user_help.delete_one({'topic_id': topic_id})
        logger.info(f"Тема {topic_id} удалена из БД")
    except Exception as e:
        logger.error(f"Ошибка при удалении темы из БД: {e}", exc_info=True)

def get_or_create_topic(bot: TeleBot, username: str, user_id: int) -> int:
    """
    Получает существующую или создает новую тему для пользователя
    """
    try:
        # Проверяем наличие темы в БД
        existing_topic = get_topic_from_db(user_id)
        if existing_topic:
            topic_id = existing_topic['topic_id']
            logger.info(f"Найдена существующая тема {topic_id} для пользователя {username}")
            
            # Проверяем, существует ли тема в группе
            if check_topic_exists(bot, topic_id):
                update_last_message_time(topic_id)
                # Устанавливаем иконку "требует внимания"
                update_topic_icon(bot, topic_id, 'attention')
                return topic_id
            else:
                # Если тема не существует, удаляем её из БД
                delete_topic_from_db(topic_id)
                logger.info(f"Тема {topic_id} была удалена из группы, создаем новую")
        
        # Создаем новую тему с иконкой лампочки
        topic_name = f"{TOPIC_ICONS['new']} {username}"
        topic = bot.create_forum_topic(
            chat_id=SUPPORT_GROUP_ID,
            name=topic_name
        )
        
        if topic:
            topic_id = topic.message_thread_id
            save_topic_to_db(user_id, topic_id, username)
            
            # Отправляем первое сообщение в тему
            bot.send_message(
                SUPPORT_GROUP_ID,
                f"Новый пользователь {username} начал диалог с поддержкой.",
                message_thread_id=topic_id
            )
            
            return topic_id
        else:
            logger.error("Не удалось создать тему")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при создании темы: {e}", exc_info=True)
        return None

def get_user_id_by_topic(topic_id: int) -> int:
    """
    Получает ID пользователя по ID темы
    """
    try:
        topic = db.nfterrium_user_help.find_one({'topic_id': topic_id})
        return topic['user_id'] if topic else None
    except Exception as e:
        logger.error(f"Ошибка при получении user_id из БД: {e}", exc_info=True)
        return None

def get_support_message_id(topic_id: int, user_message_id: int) -> int:
    """
    Получает ID сообщения в группе поддержки по ID оригинального сообщения
    """
    try:
        message = db.nfterrium_support_messages.find_one({
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

        db.nfterrium_support_messages.update_one(
            {'topic_id': topic_id, 'message_id': message_id},
            {'$set': update_data}
        )
        
        # Обновляем кэш если есть
        cache_key = f"msg_{topic_id}_{message_id}"
        if cache_key in message_cache:
            message_cache[cache_key].update(update_data)
    except Exception as e:
        logger.error(f"Ошибка при обновлении сообщения: {e}", exc_info=True)

def update_topic_icon(bot: TeleBot, topic_id: int, icon_type: str):
    """
    Обновляет иконку темы в группе поддержки и удаляет служебное сообщение
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
        topic_data = db.nfterrium_user_help.find_one({'topic_id': topic_id})
        if not topic_data:
            logger.error(f"Тема {topic_id} не найдена в БД")
            return False
            
        # Формируем новое название темы
        username = topic_data.get('username', 'Unknown')
        icon = TOPIC_ICONS[icon_type]
        new_name = f"{icon} {username}"
        
        try:
            # Запоминаем последнее сообщение перед изменением
            last_msg_before = None
            try:
                msgs = bot.get_chat_messages(
                    chat_id=SUPPORT_GROUP_ID,
                    message_thread_id=topic_id,
                    limit=1
                )
                if msgs:
                    last_msg_before = msgs[0].message_id
            except Exception as e:
                logger.warning(f"Не удалось получить последнее сообщение: {e}")
            
            # Обновляем название темы
            bot.edit_forum_topic(
                chat_id=SUPPORT_GROUP_ID,
                message_thread_id=topic_id,
                name=new_name
            )
            
            # Если у нас есть ID последнего сообщения, проверяем новые
            if last_msg_before:
                # Даем время на появление служебного сообщения
                time.sleep(1)
                
                try:
                    # Пытаемся получить последние сообщения несколько раз
                    for _ in range(3):
                        msgs = bot.get_chat_messages(
                            chat_id=SUPPORT_GROUP_ID,
                            message_thread_id=topic_id,
                            limit=3  # Получаем несколько сообщений на случай задержки
                        )
                        
                        # Проверяем все полученные сообщения
                        for msg in msgs:
                            if msg.message_id > last_msg_before and msg.text:
                                if any(phrase in msg.text.lower() for phrase in ["renamed topic", "переименовал тему", "изменил название"]):
                                    try:
                                        bot.delete_message(
                                            chat_id=SUPPORT_GROUP_ID,
                                            message_id=msg.message_id
                                        )
                                        logger.info(f"Удалено служебное сообщение {msg.message_id} о переименовании в теме {topic_id}")
                                        return True
                                    except Exception as e:
                                        logger.warning(f"Не удалось удалить служебное сообщение: {e}")
                        
                        # Если сообщение не найдено, ждем немного и пробуем снова
                        time.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Не удалось проверить новые сообщения: {e}")
            
            logger.info(f"Обновлена иконка темы {topic_id} на {icon_type}")
            return True
            
        except Exception as e:
            if "TOPIC_NOT_MODIFIED" in str(e):
                # Игнорируем ошибку, если название не изменилось
                logger.info(f"Тема {topic_id} уже имеет нужную иконку")
                return True
            raise  # Пробрасываем остальные ошибки
            
    except Exception as e:
        logger.error(f"Ошибка при обновлении иконки темы: {e}", exc_info=True)
        return False

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
        
        # Отправляем уведомление в группу поддержки
        bot.send_message(
            SUPPORT_GROUP_ID,
            f"⚠️ Пользователь отредактировал сообщение:\n{message.text}",
            message_thread_id=topic_id
        )
        
        logger.info(f"Обработано редактирование сообщеия от пользователя {user_id}")
        
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
        
        # Отправляем уведомление в группу поддержки
        bot.send_message(
            SUPPORT_GROUP_ID,
            "🗑 Пользователь удалил сообщение",
            message_thread_id=topic_id
        )
        
        logger.info(f"Обработано удаление сообщения от пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке удаления: {e}", exc_info=True)

def bot_chat_user(message: Message, bot: TeleBot):
    """
    Обработка сообщений пользователя и пересылка в группу поддержки
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username or str(user_id)
        
        # Получаем или создаем тему с использованием кэша
        topic_id = get_or_create_topic(bot, username, user_id)
        if not topic_id:
            logger.error(f"Не удалось создать тему для пользователя {username}")
            return
        
        try:
            # Пересылаем сообщение в группу поддержки
            forwarded = bot.forward_message(
                SUPPORT_GROUP_ID,
                message.chat.id,
                message.message_id,
                message_thread_id=topic_id
            )
            
            # Сохраняем сообщение в базу данных
            save_message_to_db(
                topic_id,
                user_id,
                message.text or message.caption or "",
                message.message_id,
                forwarded.message_id
            )
            
            # Обновляем время последнего сообщения
            update_last_message_time(topic_id)
            
            # Устанавливаем иконку "требует внимания"
            update_topic_icon(bot, topic_id, 'attention')
            
        except Exception as e:
            logger.error(f"Ошибка при пересылке сообщения: {e}", exc_info=True)
            bot.reply_to(message, "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Ошибка в bot_chat_user: {e}", exc_info=True)
        bot.reply_to(message, "Произошла ошибка. Пожалуйста, попробуйте позже.")

def handle_support_reply(message: Message, bot: TeleBot):
    """
    Обработка ответов из группы поддержки.
    Сообщение отправляется пользователю только если это ответ на его сообщение.
    """
    try:
        logger.info(f"Получено сообщение из чата {message.chat.id}")
        logger.info(f"Сообщение: {message.text}")
        logger.info(f"От пользователя: {message.from_user.id}")

        # Проверяем, что это сообщение из группы поддержки
        if message.chat.id != SUPPORT_GROUP_ID:
            logger.info(f"Сообщение не из группы поддержки: {message.chat.id}")
            return

        # Проверяем, что это ответ на сообщение
        if not message.reply_to_message:
            logger.info("Это не ответ на сообщение")
            return
        
        topic_id = message.message_thread_id
        if not topic_id:
            logger.info("Нет ID темы")
            return

        logger.info(f"Обработка ответа в теме {topic_id}")
        logger.info(f"Ответ на сообщение: {message.reply_to_message.message_id}")
        
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
        user_data = db.nfterrium_user_help.find_one({'topic_id': topic_id})
        if not user_data:
            logger.error(f"Не найдена информация о пользователе для темы {topic_id}")
            return

        logger.info(f"Найдены данные пользователя: {user_data}")
        
        try:
            # Сначала устанавливаем иконку "отвечено"
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

def run_bot(bot: TeleBot):
    """
    Запуск бота с обработкой ошибок и мониторингом
    """
    import psutil
    import time
    from datetime import datetime, timedelta
    
    # Инициализация БД
    init_db()
    
    # Переменные для мониторинга
    start_time = datetime.now()
    last_restart = start_time
    message_count = 0
    error_count = 0
    
    while True:
        try:
            # Проверка использования памяти
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024 / 1024  # В МБ
            
            # Если использование памяти превышает 1GB, перезапускаем бот
            if memory_usage > 1024:  # 1GB
                logger.warning(f"Высокое использование памяти ({memory_usage:.2f}MB). Перезапуск бота...")
                break
                
            # Проверка времени работы
            uptime = datetime.now() - start_time
            if uptime > timedelta(hours=12):  # Перезапуск каждые 12 часов
                logger.info(f"Плановый перезапуск после {uptime}")
                break
                
            # Сброс счетчика ошибок каждый час
            if datetime.now() - last_restart > timedelta(hours=1):
                error_count = 0
                last_restart = datetime.now()
                
            # Запуск бота
            logger.info("Запуск бота...")
            bot.polling(non_stop=True, interval=1)
            
        except Exception as e:
            error_count += 1
            logger.error(f"Ошибка в работе бота: {e}", exc_info=True)
            
            # Если много ошибок за час, перезапускаем бот
            if error_count > 10:
                logger.error("Слишком много ошибок. Перезапуск бота...")
                break
                
            time.sleep(5)  # Пауза перед повторной попыткой
            continue

# Инициализируем БД при запуске
init_db()
