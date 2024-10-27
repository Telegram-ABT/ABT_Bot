import os
from telethon import events
from pymongo import MongoClient
from datetime import datetime
from bot_support import client  # Импортируем клиент из bot_support

# Конфигурация MongoDB
mongo_url = os.getenv('MONGO_URL')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
collection_scaner_dialog = db["scanerdialog"]
collection_scaner_chats = db["scanerchats"]

async def main():
    print("Телеграм-сессия запущена и прослушивает сообщения...")

    # Получение ID текущего пользователя
    current_user = await client.get_me()
    current_user_id = current_user.id

    # Обработка всех входящих сообщений
    @client.on(events.NewMessage)
    async def handler(event):
        # Извлекаем информацию из сообщения
        from_user_id = event.sender_id  # ID пользователя, от кого пришло сообщение
        chat_id = event.chat_id  # ID чата или канала, где появилось сообщение
        message_text = event.message.message  # Текст сообщения

        # Получение названия чата
        chat_name = None
        try:
            chat = await event.get_chat()
            chat_name = chat.title if hasattr(chat, 'title') else "Личные сообщения"
        except Exception as e:
            print(f"Ошибка при получении названия чата: {e}")

        # Печать сообщения для отладки
        print("Сообщение от пользователя:")
        print(f"ID пользователя, от кого пришло сообщение: {from_user_id}")
        print(f"ID чата/канала: {chat_id}")
        print(f"Название чата/канала: {chat_name}")
        print(f"Текст сообщения: {message_text}")

        # Проверка, существует ли уже запись о чате в базе данных
        existing_chat = collection_scaner_chats.find_one({"chat_id": chat_id})
        if not existing_chat:
            chat_record = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "chat_id": chat_id,
                "chat_name": chat_name,
                "chat_discr": ""  # Пустое текстовое поле для описания
            }
            collection_scaner_chats.insert_one(chat_record)
            print("Запись о чате успешно добавлена в MongoDB:", chat_record)
        else:
            print("Запись о чате уже существует в MongoDB.")

        # Запись данных о сообщении в MongoDB
        message_record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_client": current_user_id,
            "id_user": from_user_id,
            "id_chat": chat_id,
            "chat_name": chat_name,
            "message": message_text
        }
        collection_scaner_dialog.insert_one(message_record)
        print("Запись о сообщении успешно добавлена в MongoDB:", message_record)

    # Бесконечный цикл для прослушивания сообщений
    await client.run_until_disconnected()

# Запуск основной функции
client.loop.run_until_complete(main())
