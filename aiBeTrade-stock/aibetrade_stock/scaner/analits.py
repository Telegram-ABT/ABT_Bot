from pymongo import MongoClient
import os
from bot_trade import  process_get_status_message

# Подключение к MongoDB
mongo_url = os.getenv('MONGO_URL_SERV')
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
case_share_collection = db["kogan_case_share"]
case_collection = db["kogan_case"]
sell_position_collection = db["kogan_sell_position"]

def process_pnl_selection(bot,chat_id,threshold, case_name=None):
    if case_name:
        process_get_status_message(bot, chat_id, case_name)
        process_pnl_set(bot,chat_id,threshold, case_name)
    else:
        cases = case_collection.find({"active":True})
        if cases:
            for case in cases:
                process_get_status_message(bot, chat_id, case['case_name'])
                process_pnl_set(bot,chat_id,threshold, case['case_name'])
        else:
            bot.send_message(chat_id, "Портфели не найдены")
    return "База акций сформирована"

def process_pnl_set(bot,chat_id,threshold, case_name=None):
    # Удаляем все записи из kogan_sell_position
    bot.send_message(chat_id, f"Начало формирования базы данных {case_name}")
    sell_position_collection.delete_many({'case_name':case_name,'share_sell':False})

    # Выбираем акции с PNL больше заданного порога
    query = {"case_name": case_name,} if case_name else {}
    shares = case_share_collection.find(query)
    for share in shares:
        quantity = float(share.get('quantity', 0))
        average_price = float(share.get('averagePrice', 0))
        price = float(share.get('price', 0))

        if quantity > 0 and price > 0:
            pnl = (1 - (quantity * average_price) / (quantity * price)) * 100
            if pnl > threshold:
                bot.send_message(chat_id, f"Акция {share['symbolId']} кол. {quantity} P&L {pnl:.2f}")
              # Добавляем акции в kogan_sell_position
                share_copy = share.copy()
                share_copy.pop('_id', None)
                sell_position_collection.insert_one({**share_copy,"share_sell":False,"pnl_persent":pnl})
    return
