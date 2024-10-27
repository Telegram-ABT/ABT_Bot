import os
from telethon import TelegramClient, events
from pymongo import MongoClient
from datetime import datetime
from openai import OpenAI

# Настройки для OpenAI API
key = os.environ.get('OPENAI_API_KEY')
client_openai = OpenAI(api_key=key)

# Настройки для клиента Telethon
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
USER_PHONE = os.getenv('USER_PHONE')

# Инициализация клиента Telethon
client = TelegramClient('user_session', API_ID, API_HASH, system_version="4.16.32-vxCUSTOM", device_model='FastAPI Galaxy S24 Ultra, running Android 14')

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
collection_scaner_dialog = db["scanerdialog"]
collection_scaner_chats = db["scanerchats"]
scanercall_collection = db["scanercall"]
scanersettings_collection = db["scanersettings"]

# Функция для отправки текста в ChatGPT и получения ответа
def send_to_chatgpt(prompt, text):
    try:
        response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка при отправке запроса в ChatGPT: {e}")
        return None

# Обработка всех входящих сообщений
@client.on(events.NewMessage)
async def handle_incoming_message(event):
    from_user_id = event.sender_id
    chat_id = event.chat_id
    message_text = event.message.message

    # Получение названия чата
    chat_name = None
    try:
        chat = await event.get_chat()
        chat_name = chat.title if hasattr(chat, 'title') else "Личные сообщения"
    except Exception as e:
        print(f"Ошибка при получении названия чата: {e}")

    # Запись данных о сообщении в MongoDB
    message_record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id_user": from_user_id,
        "id_chat": chat_id,
        "chat_name": chat_name,
        "message": message_text
    }
    collection_scaner_dialog.insert_one(message_record)
    print("Запись о сообщении успешно добавлена в MongoDB:", message_record)

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
                print(f"Сообщение будет отправлено пользователю {user_id}: {gpt_response} и запись обновлена.")
                user_entity = await client.get_entity(user_id)
                await client.send_message(user_entity, gpt_response)

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

# Запуск клиента и основно�� функции
async def main():
    await client.start(USER_PHONE)
    await process_scanercall_records()
    await client.run_until_disconnected()

client.loop.run_until_complete(main())

