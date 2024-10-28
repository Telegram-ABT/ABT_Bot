import os
from telethon import TelegramClient, events
from pymongo import MongoClient
from datetime import datetime
from openai import OpenAI
import asyncio
from threading import Thread

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
        print(f"Отправка в ChatGPT: Промт: {prompt}, Текст: {text}")
        response = client_openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        gpt_response = response.choices[0].message.content.strip()
        print(f"Ответ от ChatGPT: {gpt_response}")
        return gpt_response
    except Exception as e:
        print(f"Ошибка при отправке запроса в ChatGPT: {e}")
        return None

# Обработка всех входящих сообщений
@client.on(events.NewMessage)
async def handle_incoming_message(event):
    from_user_id = event.sender_id
    message_text = event.raw_text

    # Ищем запись в MongoDB по user_id
    record = scanercall_collection.find_one({"user_id": from_user_id})
    if not record:
        print(f"Запись для пользователя {from_user_id} не найдена.")
        return

    # Проверяем, был ли первый контакт
    if record.get("firstcall", False):
        # Получаем последние сообщения из чата с пользователем
        try:
            history = await client.get_messages(from_user_id, limit=10)
            history_text = "\n".join([f"{msg.sender_id}: {msg.text}" for msg in history if msg.text])
        except Exception as e:
            print(f"Ошибка при получении истории сообщений: {e}")
            history_text = "История сообщений недоступна."

        # Обновляем диалог
        updated_dialogues = record.get("dialogues", "") + f"\nПользователь ответил: {message_text}"
        
        # Получаем настройки из scanersettings
        settings = scanersettings_collection.find_one({"id_chat": record["id_chat"]})
        if not settings:
            print(f"Настройки не найдены. Пропуск обработки.")
            return

        promt = settings.get("promt", "")
        chat_discr = settings.get("chat_discr", "")
        
        # Формируем текст для ChatGPT
        chatgpt_text = (
            f"Ранее у нас была совместная переписка. "
            f"История диалога: {updated_dialogues}. "
            f"История сообщений: {history_text}. "
            f"Продолжи диалог с пользователем согласно промту: {promt}"
        )
        print(f"Сформированный текст для ChatGPT: {chatgpt_text}")

        # Получаем ответ от ChatGPT
        gpt_response = send_to_chatgpt(promt, chatgpt_text)
        if gpt_response and gpt_response.strip().upper() != "STOP":
            try:
                # Попытка получить сущность пользователя
                try:
                    user_entity = await client.get_entity(from_user_id)
                except ValueError as e:
                    print(f"Не удалось получить сущность пользователя {from_user_id}: {e}")
                    return
                
                # Обновляем диалог и отправляем ответ
                updated_dialogues += f"\nЯ ответил: {gpt_response}"
                scanercall_collection.update_one(
                    {"_id": record["_id"]},
                    {
                        "$set": {
                            "dialogues": updated_dialogues
                        }
                    }
                )
                
                # Отправляем ответ пользователю
                await client.send_message(from_user_id, gpt_response)
                print(f"Ответ отправлен пользователю {from_user_id}: {gpt_response}")
            except Exception as e:
                print(f"Ошибка при отправке ответа: {e}")
        else:
            print(f"Диалог завершен или получен STOP")

# Функция для периодической проверки новых записей
async def check_new_records():
    while True:
        try:
            # Ищем только записи, где не было первого контакта
            records = scanercall_collection.find({"firstcall": False})
            for record in records:
                print(f"\nПолучена запись для первого контакта: {record}")
                
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
                
                # Формируем текст для отправки в ChatGPT только для первого контакта
                alltext = (
                    f"Проанализируй информацию о диалогах пользователя: диалоги внизу промта, "
                    f"который беседовал в группе с названием '{chat_name}'. "
                    f"Описание группы: {chat_discr}. Диалоги идут в обратном хронологическом порядке сначала старые внизу новые. "
                    f"Если диалогов нет, то это твой первый контакт с пользователем, надо написать простое и короткое приветственное сообщение, если диалоги есть, то продолжи диалог."
                    f"Отправь только ответ без своих внутренних сообщений, как будьто это ты общаешься с пользователем. "
                    f"Если пользователь отвечает отказом или в отрицательном ключе или не желает продолжать диалог, то не продолжай диалог и ответь 'STOP'. "
                    f"{promt}"
                )
                print(f"Сформированный текст для первого контакта: {alltext}")

                # Отправка текста в ChatGPT и обработка ответа
                gpt_response = send_to_chatgpt(alltext, texts_message)
                if gpt_response and gpt_response.strip().upper() != "STOP":
                    try:
                        user_entity = await client.get_entity(user_id)
                        await client.send_message(user_entity, gpt_response)
                        
                        # Обновляем запись, устанавливая firstcall = True
                        scanercall_collection.update_one(
                            {"_id": record["_id"]},
                            {
                                "$set": {
                                    "firstcall": True,
                                    "firstcalltext": gpt_response,
                                    "dialogues": f"Я начал диалог: {gpt_response}"
                                }
                            }
                        )
                        print(f"Первое сообщение отправлено пользователю {user_id}")
                    except Exception as e:
                        print(f"Ошибка при отправке первого сообщения пользователю {user_id}: {e}")
                        continue
            
            await asyncio.sleep(60)  # Проверка новых записей каждую минуту
            
        except Exception as e:
            print(f"Ошибка при проверке новых записей: {e}")
            await asyncio.sleep(60)

# Запуск клиента и основных функций
async def main():
    await client.start(USER_PHONE)
    
    # Создаем отдельную задачу для проверки новых записей
    check_records_task = asyncio.create_task(check_new_records())
    
    # Запускаем прослушивание сообщений
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Запускаем все асинхронные задачи
    client.loop.run_until_complete(main())
