from openai import OpenAI
from pymongo import MongoClient
import os
from bot_support import send_telegram_message  # Импортируем функцию отправки сообщений
import telebot
from telebot import apihelper

# Настройки для OpenAI API
key = os.environ.get('OPENAI_API_KEY')
client_openai = OpenAI(api_key=key)

# Настройки MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
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
                await send_telegram_message(user_id, gpt_response)  # Используем функцию из bot_support

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

# Запуск основной функции
async def main():
    await process_scanercall_records()

# Вызов основной функции
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# Укажите токен вашего бота
TOKEN = os.getenv('TOKEN_BOT_SCANER')
bot = telebot.TeleBot(TOKEN)

try:
    bot.polling(none_stop=True)
except apihelper.ApiTelegramException as e:
    if "Conflict: terminated by other getUpdates request" in str(e):
        print("Конфликт: другой экземпляр бота уже запущен.")
    else:
        raise
