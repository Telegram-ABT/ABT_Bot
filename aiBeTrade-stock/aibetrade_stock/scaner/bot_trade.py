import os
import requests
import json
from requests.auth import HTTPBasicAuth
from telethon import TelegramClient, events
from pymongo import MongoClient
from datetime import datetime
from openai import OpenAI
import asyncio

# Настройки для OpenAI API
key = os.environ.get('OPENAI_API_KEY')
client_openai = OpenAI(api_key=key)

# Настройки для клиента Telethon
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
USER_PHONE = os.getenv('USER_PHONE')

# URL для отправки ордеров
api_url = 'https://api-demo.exante.eu/trade/3.0/orders'

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

# Функция для отправки ордера брокеру
def send_order_to_broker(symbol, side, quantity, account_id, application_id, application_access_key):
    print(f"Отправка ордера брокеру: {symbol} {side} {quantity}")
    order_data = {
        "accountId": account_id,
        "symbolId": symbol,
        "side": side,
        "quantity": str(quantity),
        "orderType": "market",
        "duration": "day"
    }

    response = requests.post(
        api_url,
        auth=HTTPBasicAuth(application_id, application_access_key),
        headers={'Content-Type': 'application/json'},
        data=json.dumps(order_data)
    )

    try:
        response.raise_for_status()
        print("Операция успешно выполнена:")
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Ошибка HTTP: {e}")
        print(f"Ответ от сервера: {response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка запроса: {e}")
        return None

# Функция для проверки статуса ордеров
async def check_order_status():
    while True:
        try:
            # Ищем ордера, которые не завершены
            orders = trading_collection.find({"order_status": {"$nin": ["cancelled", "filled", "rejected"]}})
            for order in orders:
                order_id = order.get("orderId")
                case_name = order.get("case")

                # Получаем application_id и application_access_key из kogan_case
                case_info = case_collection.find_one({"case_name": case_name})
                if not case_info:
                    print(f"Информация о портфеле {case_name} не найдена.")
                    continue

                application_id = case_info.get("application_id")
                application_access_key = case_info.get("application_access_key")

                # Запрос статуса ордера
                status_response = requests.get(
                    f"{api_url}/{order_id}",
                    auth=HTTPBasicAuth(application_id, application_access_key)
                )

                if status_response.status_code == 200:
                    order_status = status_response.json()["orderState"]["status"]
                    print(f"Статус ордера {order_id}: {order_status}")

                    # Обновление статуса ордера в БД
                    trading_collection.update_one(
                        {"orderId": order_id},
                        {
                            "$set": {
                                "order_status": order_status,
                                "order_details": status_response.json()  # Сохраняем полную информацию об ордере
                            }
                        }
                    )

                    # Если ордер выполнен, обновляем информацию в case_share
                    if order_status == "filled":
                        fills = status_response.json()["orderState"]["fills"]
                        total_quantity = sum(float(fill["quantity"]) for fill in fills)
                        total_sum = sum(float(fill["quantity"]) * float(fill["price"]) for fill in fills)
                        case = order["case"]
                        share = order["share"]

                        if status_response.json()["orderParameters"]["side"].upper() == "SELL":
                            total_quantity = -total_quantity
                            total_sum = -total_sum

                        # Поиск акции в БД
                        share_info = case_share_collection.find_one({"case": case, "share": share})
                        if share_info:
                            balance_count = share_info.get("balance_count", 0) + total_quantity
                            if balance_count == 0:
                                balance_sum = 0
                            else:
                                balance_sum = share_info.get("balance_sum", 0) + total_sum

                            # Обновление записи в БД
                            case_share_collection.update_one(
                                {"case": case, "share": share},
                                {"$set": {"balance_count": balance_count, "balance_sum": balance_sum}}
                            )
                            print(f"Информация в case_share обновлена для {share} в {case}")
                        else:
                            print(f"Акция {share} в портфеле {case} не найдена.")
                else:
                    print(f"Ошибка при получении статуса ордера {order_id}: {status_response.text}")

            await asyncio.sleep(10)  # Проверка статуса ордеров каждые 10 секунд

        except Exception as e:
            print(f"Ошибка при проверке статуса ордеров: {e}")
            await asyncio.sleep(10)

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
            "Название портфеля без ковычек., "
            "Название акции без изменений и только на латинице без русских названий (если указана биржа, то название акции должно быть с биржей через разделитель точка), "
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
            # Разбор ответа
            try:
                case, share, type_op, price, balance = gpt_response.strip('{}').split('}{')
                share = share.strip()
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
            case_info = case_collection.find_one({"case_name": case})
            if not case_info:
                print(f"Информация о портфеле {case} не найдена.")
                return

            account_id = case_info.get("account_id")
            application_id = case_info.get("application_id")
            application_access_key = case_info.get("application_access_key")
            case_deposit = case_info.get("case_deposit")
            active = case_info.get("active")
            print(f"Информация о портфеле: {case_info}")

            if active:
                case_share_info = case_share_collection.find_one({"case": case, "share": share})
                if not case_share_info:
                    print(f"Данных по акции {share} в портфеле {case} не обнаружено.")
                    balance_count = 0
                    balance_sum = 0
                else:
                    balance_count = case_share_info["balance_count"]
                    balance_sum = case_share_info["balance_sum"]
                    print(f"Информация по акции: {case_share_info}")

                # Расчет размера ордера
                if type_op == "BUY":
                    count_order = int((case_deposit * balance / 100) / price) if not case_share_info else int(((case_deposit * balance / 100) - balance_sum) / price)
                    sum = count_order * price
                elif type_op == "SELL":
                    if not case_share_info:
                        print("Позиция по акции не была сформирована ранее.")
                        return
                    count_order = -balance_count if balance == 0 else int(balance_count * balance / 100)
                    sum = -balance_sum if balance == 0 else count_order * price

                print(f"Рассчитанный размер ордера: {count_order} сумма {sum}")
                if balance_count + count_order < 0:
                    print(f"Количество акций {share} в портфеле {case} меньше чем размер ордера {count_order}. Действие не выполняется.")
                    return

                # Отправка ордера брокеру
                if count_order > 0:
                    broker_response = send_order_to_broker(share, type_op.lower(), abs(count_order), account_id, application_id, application_access_key)
                else:
                    broker_response = send_order_to_broker(share, type_op.lower(), abs(count_order*(-1)), account_id, application_id, application_access_key)
                print(f"Ответ от брокера: {broker_response}")

                if broker_response:
                    # Запись в таблицу trading
                    trading_data = {
                        "date": datetime.now(),
                        "case": case,
                        "share": share,
                        "type": type_op,
                        "price": price,
                        "count_order": count_order,
                        "sum": sum,
                        "orderId": broker_response[0].get("orderId"),
                        "broker_response": broker_response,
                        "order_status": broker_response[0]["orderState"].get("status")
                    }
                    trading_collection.insert_one(trading_data)
                    print(f"Данные торговой операции записаны в MongoDB: {trading_data}")

# Запуск клиента и основных функций
async def main():
    await client.start(USER_PHONE)
    print("Клиент Telegram запущен.")
    
    # Зап��ск задачи для проверки статуса ордеров
    asyncio.create_task(check_order_status())
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.loop.run_until_complete(main())
