from telebot import TeleBot
from telebot.types import Message, ForumTopic
import time
import logging
import sys
import os
import re
from pymongo import MongoClient, ASCENDING
from datetime import datetime

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

# Подключение к MongoDB
MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(MONGO_URI)
db = client.nntcapital

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
    Получает информацию о теме из базы данных
    """
    try:
        return db.nfterrium_user_help.find_one(
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
        db.nfterrium_user_help.insert_one({
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
        db.nfterrium_user_help.update_one(
            {'topic_id': topic_id},
            {'$set': {'last_message_at': datetime.utcnow()}}
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении времени: {e}", exc_info=True)

def save_message_to_db(topic_id: int, user_id: int, message_text: str, message_id: int, support_message_id: int = None, is_support: bool = False):
    """
    Сохраняет сообщение в историю
    Args:
        topic_id: ID темы
        user_id: ID поль��ователя
        message_text: Текст сообщения
        message_id: ID сообщения
        support_message_id: ID сообщения в группе поддержки (если есть)
        is_support: Флаг, указывающий что сообщение от поддержки
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
            
        db.nfterrium_support_messages.insert_one(message_data)
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
                return topic_id
            else:
                # Если тема не существует, удаляем её из БД
                delete_topic_from_db(topic_id)
                logger.info(f"Тема {topic_id} была удалена из группы, создаем новую")
            
        logger.info(f"Создание новой темы для пользователя {username} (ID: {user_id})")
        
        # Создаем новую тему
        new_topic = bot.create_forum_topic(
            SUPPORT_GROUP_ID,
            name=username
        )
        
        topic_id = new_topic.message_thread_id
        
        # Сохраняем в БД
        save_topic_to_db(user_id, topic_id, username)
        
        # Отправляем первое сообщение в тему
        bot.send_message(
            SUPPORT_GROUP_ID,
            f"Новый пользователь <a href='tg://user?id={user_id}'>@{username}</a>",
            parse_mode='HTML',
            message_thread_id=topic_id
        )
        
        logger.info(f"Создана новая тема: {topic_id} для пользователя {user_id}")
        return topic_id
            
    except Exception as e:
        logger.error(f"Ошибка при создании/получении темы: {e}", exc_info=True)
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
        
        logger.info(f"Обработано удаление сообщ��ния от пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке удаления: {e}", exc_info=True)

def bot_chat_user(message: Message, bot: TeleBot):
    """
    Обработка сообщений пользователя и пересылка в группу поддержки
    """
    try:
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        logger.info(f"Получено сообщение от пользователя {username} (ID: {user_id})")
        
        # Получаем или создаем тему для пользователя
        topic_id = get_or_create_topic(bot, username, user_id)
        
        if topic_id:
            try:
                # Пересылаем сообщение в тему группы поддержки
                forwarded = bot.forward_message(
                    SUPPORT_GROUP_ID,
                    message.chat.id,
                    message.message_id,
                    message_thread_id=topic_id
                )
                logger.info(f"Сообщение переслано в тему {topic_id}")
                
                # Сохраняем сообщение в историю
                save_message_to_db(
                    topic_id=topic_id,
                    user_id=user_id,
                    message_text=message.text or "",  # На случай если сообщение без текста
                    message_id=message.message_id,
                    support_message_id=forwarded.message_id
                )
                
                # Обновляем время последнего сообщения
                update_last_message_time(topic_id)
                
                # Отправляем подтверждение пользователю
            except Exception as e:
                if "message thread not found" in str(e):
                    logger.warning("Тема была удалена, пробуем создать новую")
                    # Удаляем старую тему из БД
                    delete_topic_from_db(topic_id)
                    # Рекурсивно пробуем еще раз
                    bot_chat_user(message, bot)
                else:
                    logger.error(f"Ошибка при пересылке сообщения: {e}", exc_info=True)
                    bot.reply_to(message, "Произошла ошибка при отправке сообщения в поддержку.")
        else:
            logger.error("Не удалось создать тему для сообщения")
            bot.reply_to(message, "Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Общая ошибка в bot_chat_user: {e}", exc_info=True)
        bot.reply_to(message, "Произошла ошибка при обработке вашего сообщения.")

def handle_support_reply(message: Message, bot: TeleBot):
    """
    Обработка ответов из группы поддержки
    """
    try:
        # Проверяем, что сообщение из группы поддержки
        if message.chat.id != SUPPORT_GROUP_ID:
            logger.info(f"Сообщение не из группы поддержки: {message.chat.id}")
            return
            
        if not message.message_thread_id:
            logger.warning("Сообщение не в теме")
            return
            
        logger.info(f"Обработка сообщения из группы поддержки. Thread ID: {message.message_thread_id}")
            
        # Проверяем, что это ответ на сообщение
        if not message.reply_to_message:
            logger.info("Внутреннее обсуждение в группе поддержки (не ответ)")
            return
            
        logger.info(f"Это ответ на сообщение: {message.reply_to_message.message_id}")
        
        # Проверяем, что это ответ на сообщение пользователя, а не на сообщение поддержки
        replied_message = db.nfterrium_support_messages.find_one({
            'topic_id': message.message_thread_id,
            'support_message_id': message.reply_to_message.message_id
        })
        
        if replied_message and replied_message.get('is_support'):
            logger.info("Ответ на сообщение поддержки, пропускаем")
            return
            
        # Если сообщение не найдено в базе или это не сообщение поддержки,
        # значит это либо сообщение пользователя, либо первое сообщение в теме
        if not replied_message:
            # Проверяем, не является ли это ответом на первое сообщение в теме
            if not message.reply_to_message.text or not message.reply_to_message.text.startswith("Новый пользователь"):
                logger.info("Сообщение не найдено в базе и это не первое сообщение темы, пропускаем")
                return
        
        # Получаем ID пользователя из БД по ID темы
        user_id = get_user_id_by_topic(message.message_thread_id)
        logger.info(f"Найден пользователь для темы {message.message_thread_id}: {user_id}")
        
        if not user_id:
            logger.error("Не найден пользователь для темы")
            bot.reply_to(message, "Не удалось найти пользователя для этой темы")
            return
        
        try:
            # Отправляем ответ пользователю
            logger.info(f"Отправляем ответ пользователю {user_id}: {message.text}")
            sent_message = bot.send_message(
                chat_id=user_id,
                text=message.text,
                parse_mode='HTML'
            )
            
            logger.info(f"Сообщение успешно отправлено пользователю, message_id: {sent_message.message_id}")
            
            # Сохраняем ответ в историю
            save_message_to_db(
                topic_id=message.message_thread_id,
                user_id=message.from_user.id,
                message_text=message.text or "",
                message_id=message.message_id,
                support_message_id=sent_message.message_id,
                is_support=True
            )
            
            # Обновляем время последнего сообщения
            update_last_message_time(message.message_thread_id)
            
            # Подтверждаем отправку
            bot.reply_to(
                message,
                "✅ Ответ отправлен пользователю"
            )
            
        except Exception as e:
            error_msg = f"Ошибка при отправке ответа: {str(e)}"
            logger.error(error_msg, exc_info=True)
            bot.reply_to(message, f"Ошибка при отправке ответа пользователю: {error_msg}")
            
    except Exception as e:
        logger.error(f"Общая ошибка в handle_support_reply: {e}", exc_info=True)
        bot.reply_to(message, "Произошла ошибка при обработке ответа")

# Инициализируем БД при запуске
init_db()
