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
signal_collection = db["kogan_signal"]
case_collection = db["kogan_case"]
case_share_collection = db["kogan_case_share"]
trading_collection = db["kogan_trading"]

# Функция для отправки текста в ChatGPT и получения ответа
def send_to_chatgpt(prompt, text):
    try:
        print(f"Отправка в ChatGPT: Промт: {prompt}, Текст: {text}")
        response = client_openai.chat.completions.create(
            model="gpt-4o",
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
    message_text = event.raw_text
    print(f"Получено сообщение: {message_text}")

    if "#push" in message_text:
        print("Обнаружен #push в сообщении.")
        # Новый промт
        promt = (
            "Преобразуй сообщение в следующую структуру: "
            "Название портфеля без ковычек., Название акции только на латинице без русских названий, "
            "Тип сигнала: BUY или SELL, Цена акции, Процент остатка акции в портфеле без знака процент. "
            "Дробные разделители точка. "
            "Структура должна включать в себя разделители данных {} и между разделителями данных не должно быть пробелов. "
            "Особенности сообщения. Иногда сообщение содержит информацию о продаже акции и не содержит ни процента продажи, "
            "ни процента остатка акций в портфеле это означает что продается все что есть и в этом случае процент остатка в портфеле будет 0. "
            "В финале проверить на соответствие полученного результата следующей структуре: "
            "{Название портфеля}{название акции}{тип сигнала}{Цена акции}{Процент остатка}. "
            "В случае, если исходное сообщение не содержит данных по указанной структуре, то данное сообщение игнорировать."
        )
        gpt_response = send_to_chatgpt(promt, message_text)

        if gpt_response:
            print(f"Ответ от ChatGPT получен: {gpt_response}")
            # Разб��р ответа
            try:
                case, share, type_op, price, balance = gpt_response.strip('{}').split('}{')
                price = float(price)
                balance = float(balance)
                print(f"Разобранные данные: case={case}, share={share}, type={type_op}, price={price}, balance={balance}")
            except Exception as e:
                print(f"Ошибка при разборе ответа: {e}")
                return

            # Запись в MongoDB
            signal_data = {
                "date": datetime.now(),
                "case_name": case,
                "share": share,
                "type": type_op,
                "price": price,
                "balance": balance
            }
            signal_collection.insert_one(signal_data)
            print(f"Данные сигнала записаны в MongoDB: {signal_data}")

            # Обработка ответа
            print(f"Поиск информации о портфеле: {case}")
            # Отладочный вывод всех записей в коллекции

            case_info = case_collection.find_one({"case_name": case})
            if not case_info:
                print(f"Информация о портфеле {case} не найдена.")
                return

            case_deposit = case_info.get("case_deposit")
            active = case_info.get("active")
            print(f"Информация о портфеле: {case_info}")

            if active:
                case_share_info = case_share_collection.find_one({"case": case, "share": share})
                if not case_share_info:
                    print(f"Данных по акции {share} в портфеле {case} не обнаружено.")
                    return

                balance_count = case_share_info["balance_count"]
                balance_sum = case_share_info["balance_sum"]
                print(f"Информация по акции: {case_share_info}")

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

                print(f"Рассчитанный размер ордера: {count_order}")

                # Запись в таблицу trading
                trading_data = {
                    "date": datetime.now(),
                    "case": case,
                    "share": share,
                    "type": type_op,
                    "price": price,
                    "count_order": count_order,
                    "sum": case_deposit * balance / 100 - balance_sum
                }
                trading_collection.insert_one(trading_data)
                print(f"Данные торговой операции записаны в MongoDB: {trading_data}")

                # Обновление информации в case_share
                case_share_collection.update_one(
                    {"case": case, "share": share},
                    {"$inc": {"balance_count": count_order, "balance_sum": trading_data["sum"]}}
                )
                print(f"Информация в case_share обновлена для {share} в {case}")

                # Вывод информации
                print(f"Операция выполнена: {type_op} {count_order} акций {share} в портфеле {case}")

# Запуск клиента и основных функций
async def main():
    await client.start(USER_PHONE)
    print("Клиент Telegram запущен.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
