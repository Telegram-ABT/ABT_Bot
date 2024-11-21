from pymongo import MongoClient
import os

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
case_share_collection = db["kogan_case_share"]
sell_position_collection = db["kogan_sell_position"]

def process_pnl_selection(bot,chat_id,threshold, case_name=None):
    # Удаляем все записи из kogan_sell_position
    sell_position_collection.delete_many({})

    # Выбираем акции с PNL больше заданного порога
    query = {"case_name": case_name} if case_name else {}
    shares = case_share_collection.find(query)
    for share in shares:
        bot.send_message(chat_id, f"Акция {share['case_name']} {share['symbol']}")
        quantity = share.get('quantity', 0)
        average_price = share.get('averagePrice', 0)
        price = share.get('price', 0)

        if quantity > 0 and price > 0:
            pnl = (1 - (quantity * average_price) / (quantity * price)) * 100
            if pnl > threshold:
                # Добавляем акции в kogan_sell_position
                sell_position_collection.insert_one(share)

    return "База акций сформирована"
