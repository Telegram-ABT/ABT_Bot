import os
from pymongo import MongoClient
from datetime import datetime
from bot_support import send_telegram_message  # Импортируем функцию отправки сообщений

# Конфигурация MongoDB
mongo_url = os.getenv('MONGO_URL')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
collection_scaner_dialog = db["scanerdialog"]
collection_scaner_chats = db["scanerchats"]

async def process_messages():
    print("Обработка сообщений...")

    # Здесь можно добавить логику для обработки сообщений
    # Например, отправить сообщение через send_telegram_message

# Запуск основной функции
async def main():
    await process_messages()

# Вызов основной функции
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
