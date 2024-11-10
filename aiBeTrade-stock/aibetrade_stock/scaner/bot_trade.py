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
client = TelegramClient('user_session_trade', API_ID, API_HASH)

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
signal_collection = db["signal"]
case_collection = db["case"]
case_share_collection = db["case_share"]
trading_collection = db["trading"]

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
    message_text = event.raw_text

    if "#push" in message_text:
        # Отправка в ChatGPT
        promt = 'https://docs.google.com/document/d/16KdZVK4a_QiM7wmMCmV-42XX9dB9FtsmNvYj4NCAJ7o/edit?usp=sharing'
        gpt_response = send_to_chatgpt(promt, message_text)

        if gpt_response:
            # Разбор ответа
            try:
                case, share, type_op, price, balance = gpt_response.strip('{}').split('}{')
                price = float(price)
                balance = float(balance)
            except Exception as e:
                print(f"Ошибка при разборе ответа: {e}")
                return

            # Запись в MongoDB
            signal_data = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "case": case,
                "share": share,
                "type": type_op,
                "price": price,
                "balance_start": balance,
                "balance_lock": 0,
                "balance_free": balance
            }
            signal_collection.insert_one(signal_data)

            # Обработка ответа
            case_info = case_collection.find_one({"case_name": case})
            if not case_info:
                print(f"Информация о портфеле {case} не найдена.")
                return

            case_name = case_info["case_name"]
            case_deposit = case_info["case_deposit"]
            active = case_info["active"]

            if active:
                case_share_info = case_share_collection.find_one({"case": case, "share": share})
                if not case_share_info:
                    print(f"Данных по акции {share} в портфеле {case} не обнаружено.")
                    return

                balance_count = case_share_info["balance_count"]
                balance_sum = case_share_info["balance_sum"]

                # Расчет размера ордера
                if type_op == "BUY":
                    if not case_share_info:
                        count_order = int((case_deposit * balance / 100) / price)
                    else:
                        count_order = int(((case_deposit * balance / 100) - balance_sum) / price)
                elif type_op == "SELL":
                    if not case_share_info:
                        print("Позиция по акции не была сформирована ранее.")
                        return
                    if balance == 0:
                        count_order = balance_count
                    else:
                        count_order = int(((case_deposit * balance / 100) - balance_sum) / price)

                # Запись в таблицу trading
                trading_data = {
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "case": case,
                    "share": share,
                    "type": type_op,
                    "price": price,
                    "count_order": count_order,
                    "sum": case_deposit * balance / 100 - balance_sum
                }
                trading_collection.insert_one(trading_data)

                # Обновление информации в case_share
                case_share_collection.update_one(
                    {"case": case, "share": share},
                    {"$inc": {"balance_count": count_order, "balance_sum": trading_data["sum"]}}
                )

                # Вывод информации
                print(f"Операция выполнена: {type_op} {count_order} акций {share} в портфеле {case} по цене {price}")

# Запуск клиента и основных функций
async def main():
    await client.start(USER_PHONE)
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
