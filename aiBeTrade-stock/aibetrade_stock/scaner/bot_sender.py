import openai
from pymongo import MongoClient
from telethon import TelegramClient, events
from telethon.errors import RPCError
from datetime import datetime
import time
import os

# Настройки для ChatGPT API
key = os.environ.get('OPENAI_API_KEY')
openai.api_key = key

# Настройки MongoDB
mongo_url = os.getenv('MONGO_URL')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
scanercall_collection = db["scanercall"]
scanersettings_collection = db["scanersettings"]

# Настройки для клиента Telethon
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
USER_PHONE = os.getenv('USER_PHONE')

# Инициализация клиента Telethon
client = TelegramClient('session_name2', API_ID, API_HASH, system_version="4.16.32-vxCUSTOM", device_model='FastAPI Galaxy S24 Ultra, running Android 14')

# Функция для отправки текста в ChatGPT и получения ответа
def send_to_chatgpt(prompt, text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"Ошибка при отправке запроса в ChatGPT: {e}")
        return None

# Основная функция обработки записей из БД
async def process_scanercall_records():
    print("Запуск скрипта обработки записей")
    records = scanercall_collection.find({"firstcall": False})
    for record in records:
        print(f"\nПолучена запись: {record}")
        
        user_id = record["user_id"]
        id_chat = record["id_chat"]
        texts_message = record.get("texts_message", "")
        chat_discr = record.get("chat_discr", "")
        chat_name = record.get("chat_name", "")
        
        # Получаем настройки из таблицы scanersettings
        settings = scanersettings_collection.find_one({"id_chat": id_chat})
        if settings:
            promt = settings.get("promt", "")
            print(f"Получен promt: {promt}")
        else:
            print(f"Настройки для чата {id_chat} не найдены. Пропуск записи.")
            continue
        
        # Формируем текст для отправки в ChatGPT с новым форматом
        alltext = (
            f"Проанализируй информацию о диалогах пользователя: диалоги внизу промта, "
            f"который беседовал в группе с названием '{chat_name}'. "
            f"Описание группы: {chat_discr}. "
            f"{promt}"
        )
        print(f"Сформирован текст для отправки: {alltext}")

        # Отправка текста в ChatGPT
        print("Отправка запроса в ChatGPT")
        gpt_response = send_to_chatgpt(alltext, texts_message)

        if gpt_response:
            try:
                await send_message(user_id, gpt_response, record["_id"])
                # Обновляем запись в MongoDB
                scanercall_collection.update_one(
                    {"_id": record["_id"]},
                    {
                        "$set": {
                            "firstcall": True,
                            "firstcalltext": gpt_response
                        }
                    }
                )
                print(f"Сообщение успешно отправлено пользователю {user_id} и запись обновлена.")
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                continue
        else:
            print(f"Не удалось получить ответ от ChatGPT для пользователя {user_id}. Переход к следующей записи.")

    print("Завершение скрипта")

# Функция для отправки сообщения пользователю через Telegram клиент
async def send_message(user_id, message_text, record_id):
    try:
        # Явно получаем entity пользователя
        user_entity = await client.get_entity(user_id)
        
        await client.send_message(user_entity, message_text)
        print(f"Сообщение для {user_id}: {message_text}")
        time.sleep(1)  # Задержка для предотвращения спама

        # Обновляем запись в MongoDB, если отправка успешна
        scanercall_collection.update_one(
            {"_id": record_id},
            {"$set": {"result_call": True}}
        )
    except RPCError as e:
        print(f"Ошибка при отправке сообщения: {e}")

        # Обновляем запись в MongoDB, если произошла ошибка отправки
        scanercall_collection.update_one(
            {"_id": record_id},
            {"$set": {"result_call": False}}
        )

# Обработчик входящих сообщений
@client.on(events.NewMessage)
async def handle_incoming_message(event):
    user_id = event.sender_id
    user_message = event.raw_text
    print(f"Получено новое сообщение от пользователя {user_id}: {user_message}")

    # Ищем запись в MongoDB по user_id
    record = scanercall_collection.find_one({"user_id": user_id})
    if not record:
        print(f"Запись для пользователя {user_id} не найдена. Никаких действий не требуется.")
        return

    # Обновляем поле dialogues, добавляя новый ответ пользователя
    updated_dialogues = record.get("dialogues", "") + f"\nПользователь ответил: {user_message}"
    scanercall_collection.update_one(
        {"_id": record["_id"]},
        {"$set": {"dialogues": updated_dialogues}}
    )

    # Формируем текст для ChatGPT
    id_chat = record["id_chat"]
    chat_name = record.get("chat_name", "Личные сообщения")
    chat_discr = record.get("chat_discr", "Личные сообщения")
    firstcalltext = record.get("firstcalltext", "")
    texts_message = record.get("texts_message", "")

    # Получаем promt из таблицы scanersettings
    settings = scanersettings_collection.find_one({"id_chat": id_chat})
    if settings:
        promt = settings.get("promt", "")
    else:
        print(f"Настройки для чата {id_chat} не найдены. Пропуск обработки.")
        return

    chatgpt_text = (
        f"Ранее у нас была совместная переписка в одном из чатов '{chat_name}', "
        f"чат про '{chat_discr}'. Диалоги пользователя: {texts_message}. "
        f"Я ему написал: '{firstcalltext}', и он мне ответил: '{updated_dialogues}'. "
        f"Продолжи диалог с пользователем."
    )

    # Отправляем текст в ChatGPT
    gpt_response = send_to_chatgpt(promt, chatgpt_text)
    if gpt_response:
        # Обновляем поле dialogues, добавляя ответ от ChatGPT
        updated_dialogues += f"\nЯ ответил пользователю: {gpt_response}"
        scanercall_collection.update_one(
            {"_id": record["_id"]},
            {"$set": {"dialogues": updated_dialogues}}
        )
        print(f"Ответ будет отправлен пользователю {user_id}: {updated_dialogues}")

        # Отправляем ответ пользователю в Telegram
        user_entity = await client.get_entity(user_id)  # Повторно получаем entity перед отправкой
        await client.send_message(user_entity, gpt_response)
        print(f"Ответ отправлен пользователю {user_id}: {gpt_response}")
    else:
        print(f"Не удалось получить ответ от ChatGPT для пользователя {user_id}.")

# Запуск клиента и основной функции
async def main():
    await client.start(USER_PHONE)
    await process_scanercall_records()
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
