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

# Инициализация клиента Telethon с уникальным именем сессии
client = TelegramClient('user_session_scaner', API_ID, API_HASH, system_version="4.16.32-vxCUSTOM", device_model='FastAPI Galaxy S24 Ultra, running Android 14')

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
promtdialogs_collection = db["promtdialogs"]
promtcall_collection = db["promtcall"]
promtsettings_collection = db["promtsettings"]

async def main():
    await client.start(USER_PHONE)
    print("Телеграм-сессия запущена и прослушивает сообщения...")

    # Получаем первую запись из promtsettings
    promt_record = promtsettings_collection.find_one()
    if not promt_record:
        print("Промт не найден в таблице promtsettings.")
        return

    promt = promt_record.get("promt", "")
    print(f"Загружен промт: {promt}")

    # Обработка всех входящих сообщений
    @client.on(events.NewMessage)
    async def handler(event):
        from_user_id = event.sender_id
        message_text = event.raw_text
        chat_id = event.chat_id

        # Получение информации о пользователе
        try:
            user_entity = await client.get_entity(from_user_id)
            user_name = user_entity.first_name or "Неизвестно"
            user_login = user_entity.username or "Нет логина"
        except Exception as e:
            print(f"Ошибка при получении информации о пользователе: {e}")
            user_name = "Неизвестно"
            user_login = "Нет логина"

        # Запись данных о сообщении в MongoDB
        message_record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "id_user": from_user_id,
            "user_name": user_name,
            "user_login": user_login,
            "id_chat": chat_id,
            "message": message_text
        }
        promtdialogs_collection.insert_one(message_record)
        print("Запись о сообщении успешно добавлена в MongoDB:", message_record)

        # Формируем текст для ChatGPT
        chatgpt_text = f"{promt} Получил сообщение от пользователя, проверь в сообщении содержиться информация о моем профиле работы или нет. Если не содержиться, то отправь 'NO', если содержиться то отправь 'YES: Ответ пользователю о том, что ты предоставляешь такую услугу' {message_text}"
        print(f"Сформированный текст для ChatGPT: {chatgpt_text}")

        # Отправка текста в ChatGPT и обработка ответа
        gpt_response = await send_to_chatgpt(promt, chatgpt_text)
        if gpt_response:
            print(f"Ответ от ChatGPT: {gpt_response}")
            if "YES" in gpt_response:
                response_to_user = gpt_response.replace("YES", "").strip()
                await client.send_message(from_user_id, response_to_user)
                print(f"Ответ отправлен пользователю {from_user_id}: {response_to_user}")

                # Добавляем пользователя в promtcall
                promtcall_collection.insert_one({
                    "user_id": from_user_id,
                    "texts_message": message_text,
                    "chat_name": user_name,
                    "id_chat": chat_id,
                    "firstcall": True,
                    "dialogues": f"Я начал диалог: {response_to_user}"
                })
                print(f"Пользователь {from_user_id} добавлен в promtcall.")
            else:
                print("Ответ от ChatGPT не содержит 'YES'. Никаких действий не требуется.")

    # Бесконечный цикл для прослушивания сообщений
    await client.run_until_disconnected()

# Запуск клиента и вызов основной функции
with client:
    client.loop.run_until_complete(main())

# Асинхронная функция для отправки текста в ChatGPT и получения ответа
async def send_to_chatgpt(prompt, text):
    try:
        print(f"Отправка в ChatGPT: Промт: {prompt}, Текст: {text}")
        response = await client_openai.chat.completions.create(
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
