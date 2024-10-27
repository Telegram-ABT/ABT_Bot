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
    message_text = event.raw_text

    # Получение информации о пользователе
    user_entity = await client.get_entity(from_user_id)
    user_name = user_entity.first_name or "Неизвестно"
    user_login = user_entity.username or "Нет логина"

    # Получение названия чата
    chat_name = None
    try:
        chat = await event.get_chat()
        if hasattr(chat, 'title'):
            chat_name = chat.title
        else:
            # Если это личное сообщение, используем имя пользователя
            chat_name = user_name
    except Exception as e:
        print(f"Ошибка при получении названия чата: {e}")

    # Запись данных о сообщении в MongoDB
    message_record = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "id_user": from_user_id,
        "user_name": user_name,
        "user_login": user_login,
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

    # Ищем запись в MongoDB по user_id
    record = scanercall_collection.find_one({"user_id": from_user_id})
    if not record:
        print(f"Запись для пользователя {from_user_id} не найдена. Никаких действий не требуется.")
        return

    # Обновляем поле dialogues, добавляя новый ответ пользователя
    updated_dialogues = record.get("dialogues", "") + f"\nПользователь ответил: {message_text}"
    scanercall_collection.update_one(
        {"_id": record["_id"]},
        {"$set": {"dialogues": updated_dialogues}}
    )

    # Если firstcall = true, продолжаем диалог
    if record.get("firstcall", False):
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
            print(f"Ответ будет отправлен пользователю {from_user_id}: {updated_dialogues}")

            # Отправляем ответ польователю в Telegram
            user_entity = await client.get_entity(from_user_id)
            await client.send_message(user_entity, gpt_response)
            print(f"Ответ отправлен пользователю {from_user_id}: {gpt_response}")
        else:
            print(f"Не удалось получить ответ от ChatGPT для пользователя {from_user_id}.")

# Основная функция обработки записей из БД и отправка сообщений
async def process_scanercall_records():
    print("Запуск скрипта обработки записей")
    records = scanercall_collection.find({"firstcall": False})
    for record in records:
        print(f"\nПолучена запись: {record}")
        
        user_id = record["user_id"]
        id_chat = record["id_chat"]
        texts_message = record.get("texts_message", "")
        chat_name = record.get("chat_name", "")

        # Получаем настройки из таблицы scanersettings
        settings = scanersettings_collection.find_one({"id_chat": id_chat})
        if settings:
            promt = settings.get("promt", "")
            chat_discr = settings.get("chat_discr", "")
            print(f"Получен promt: {promt}")
        else:
            print(f"Настройки для чата {id_chat} не найдены. Пропуск записи.")
            continue
        
        # Формируем текст для отправки в ChatGPT с новым форматом
        alltext = (
            f"Проанализируй информацию о диалогах пользователя: диалоги внизу промта, "
            f"который беседовал в группе с названием '{chat_name}'. "
            f"Описание группы: {chat_discr}. Диалоги идут в обратном хронологическом порядке сначала старые внизу новые. "
            f"Отправь только ответ без своих внутренних сообщений, как будьто это ты общаешься с пользователем. "
            f"Если пользователь отвечает отказом или в отрицательном ключе или не желает продолжать диалог, то не продолжай диалог и ответь 'STOP'. "
            f"{promt}"
        )
        print(f"Сформирован текст для отправки: {alltext}")

        # Отправка текста в ChatGPT
        print("Отправка запроса в ChatGPT")
        gpt_response = send_to_chatgpt(alltext, texts_message)

        if gpt_response and gpt_response.strip().upper() != "STOP":
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
                            "firstcalltext": gpt_response,
                            "dialogues": record.get("dialogues", "") + f"\nЯ ответил пользователю: {gpt_response}"
                        }
                    }
                )
                print(f"Сообщение успешно отправлено пользователю {user_id} и запись обновлена.")
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                continue
        else:
            print(f"Ответ от ChatGPT: {gpt_response}. Переход к следующей записи.")

    print("Завершение скрипта")

# Запуск клиента и основной функции
async def main():
    await client.start(USER_PHONE)
    await process_scanercall_records()
    await client.run_until_disconnected()

client.loop.run_until_complete(main())
