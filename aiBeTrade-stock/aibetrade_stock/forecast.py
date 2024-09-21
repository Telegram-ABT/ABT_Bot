from datetime import datetime, timedelta
# import workYDB
# from workYDB import *
# import redis
# import json
from chat import GPT
from dotenv import load_dotenv
import os
from pprint import pprint
import time
import requests
from workBinance import get_BTC_analit_for, get_price_now
# from loguru import logger
import random 
# from workFlask import send_message
from postgreWork import *
import aiohttp
load_dotenv()
# sql = workYDB.Ydb()

gpt = GPT()

# GPT.set_key(os.getenv('KEY_AI'))
TOKEN_BOT_FORECAST=os.getenv('TOKEN_BOT_FORECAST')
STOCK_URL = os.environ.get('STOCK_URL')

coins = {'Bitcoin':'BTCUSDT', 
    'Ethereum':'ETHUSDT',
    'Bnb':'BNBUSDT',
    'Ripple':'XRPUSDT',
    'Cardano':'ADAUSDT',
    'Dogecoin':'DOGEUSDT',
    'Solana':'SOLUSDT',
    'Tron':'TRXUSDT',
    'Polkadot':'DOTUSDT',
    'Polygon':'MATICUSDT'}

coins2 =[ 
    {'name': 'Bitcoin', 'code': 'BTCUSDT'},
    {'name': 'Ethereum', 'code': 'ETHUSDT'},
    {'name': 'Bnb', 'code': 'BNBUSDT'},
    {'name': 'Ripple', 'code': 'XRPUSDT'},
    {'name': 'Cardano', 'code': 'ADAUSDT'},
    {'name': 'Dogecoin', 'code': 'DOGEUSDT'},
    {'name': 'Solana', 'code': 'SOLUSDT'},
    {'name': 'Tron', 'code': 'TRXUSDT'},
    {'name': 'Polkadot', 'code': 'DOTUSDT'},
    {'name': 'Polygon', 'code': 'MATICUSDT'}]
#datetime
def time_epoch():
    from time import mktime
    dt = datetime.now()
    sec_since_epoch = mktime(dt.timetuple()) + dt.microsecond/1000000.0

    millis_since_epoch = sec_since_epoch * 1000
    return int(millis_since_epoch)

def get_dates_YDB(day):
    # Текущая дата
    #patern = '2023-07-18T20:26:32'
    patern = '%Y-%m-%dT%H:%M:%SZ'
    current_date = datetime.now().strftime(patern)

    # Дата, отстоящая на 30 дней
    delta = timedelta(days=day)
    future_date = (datetime.now() + delta).strftime(patern)

    return current_date, future_date

def get_dates(day, pattern = '%d/%m/%Y'):
    # Текущая дата
    current_date = datetime.now().strftime(pattern)

    # Дата, отстоящая на 30 дней
    delta = timedelta(days=day)
    future_date = (datetime.now() + delta).strftime(pattern)

    return current_date, future_date

def timestamp_to_date(timestap, pattern='%Y-%m-%dT%H:%M:%SZ'):
   
    a = time.gmtime(timestap)
    date_time = datetime(*a[:6])
    date_string = date_time.strftime(pattern)
    
    return date_string

def date_now():
    patern = '%Y-%m-%dT%H:00:00'
    current_date = datetime.now().strftime(patern)
    return current_date+'Z'

def prepare_prognoz(text):
    import re
    pattern = r"\d+\.\d+"
    matches = re.findall(pattern, text)
    lowerPrice = 0
    upperPrice = 0
    if len(matches)==3:
        prognozPrice = matches[0]
        lowerPrice = matches[1]
        upperPrice = matches[2]
    elif len(matches)==4:
        prognozPrice = matches[0]
        lowerPrice = matches[2]
        upperPrice = matches[3]
    else:
        prognozPrice = matches[0]
    return prognozPrice, lowerPrice, upperPrice

def forecastText(day:int, coin='Bitcoin'):
    dateNow = date_now()

    #TODO взять последний от этого часа прогноз
    # rows = sql.select_query('prognoz_text',f"date = CAST('{dateNow}' as datetime) and coin = '{coin}'")
    # if rows != []:
    #     text = rows[0]['textPrognoz']
    #     return text
    promtUrl = 'https://docs.google.com/document/d/1_Ft4sDJJpGdBX8k2Et-OBIUtvO0TSuw8ZSjbv5r7H7I/edit?usp=sharing'
    PROMT_URL = promtUrl 
    #promt = gpt.load_prompt(promptUrl)
    try:
        promt = gpt.load_prompt(PROMT_URL)
    except:
        time.sleep(60)
        promt = gpt.load_prompt(PROMT_URL)
    #promt = 
    #print(f'{promptUrl=}')
    
    #print(f'{analitBTC}')
    analitBTC = get_BTC_analit_for(day, coin)
    current, future = get_dates(day)
    priceNow = str(get_price_now(coin)) 

    print("Текущая дата:", current)
    print(f"Дата через {day} дней:", future)
    promt = promt.replace('[analitict]', analitBTC)
    promt = promt.replace('[nextDate]', str(day))
    promt = promt.replace('[coin]', coin)
    promt = promt.replace('[nowDate]', future)
    promt = promt.replace('[exchangerate]', priceNow)

    print('#########################################', promt)
    try:
        mess = [{'role': 'system', 'content': promt,},
                {'role': 'user', 'content': ' '}]
        random_time = random.randint(5, 30)
        #time.sleep(random_time)
        #answer, allToken, allTokenPrice= gpt.answer(' ',mess,)
        
        primt1URL = 'https://docs.google.com/document/d/1kvtS8FDYQ7Mg0QTuIYLUzfzPzIwNtNAy8nVHTDcmH1A/edit?usp=sharing'
        promt = gpt.load_prompt(primt1URL)
        promt = promt.replace('[analitict]', analitBTC)
        promt = promt.replace('[nextDate]', str(day))
        promt = promt.replace('[coin]', coin)
        promt = promt.replace('[nowDate]', future)
        promt = promt.replace('[exchangerate]', priceNow)
        mess = [{'role': 'system', 'content': promt,},
                {'role': 'user', 'content': ' '}]
        answer1, allToken1, allTokenPrice1= gpt.answer(' ',mess,)
        
        random_time = random.randint(5, 30)
        #time.sleep(random_time)
        primt2URL= 'https://docs.google.com/document/d/15nj87WI9Ud3EGgmp0JM0AZdQVQGPgN3ly-zjWCEUsB0/edit?usp=sharing'
        promt = gpt.load_prompt(primt2URL)
        promt = promt.replace('[analitict]', analitBTC)
        promt = promt.replace('[nextDate]', str(day))
        promt = promt.replace('[coin]', coin)
        promt = promt.replace('[nowDate]', future)
        promt = promt.replace('[exchangerate]', priceNow)
        mess = [{'role': 'system', 'content': promt,},
                {'role': 'user', 'content': ' '}]
        answer2, allToken2, allTokenPrice2= gpt.answer(' ',mess,)
        

        primt3URL= 'https://docs.google.com/document/d/17hsm51kQGnhXgU7LkFkCGxsIBY82FPefowN8GcGIa6U/edit?usp=sharing'
        promt = gpt.load_prompt(primt3URL)
        mess = [{'role': 'system', 'content': promt,},
                {'role': 'user', 'content': f"{answer1}\n{answer2}"}]
        answer3, allToken3, allTokenPrice3= gpt.answer(' ',mess,)
        
        random_time = random.randint(5, 30)
        #time.sleep(random_time)
        primt4URL= 'https://docs.google.com/document/d/1cqDETdeSLj2vX8nBzWFbNV4jAl61oz_nGwL16EM-ZIM/edit?usp=sharing'
        promt = gpt.load_prompt(primt4URL)
        promt = promt.replace('[language]', 'Russian')

        mess = [{'role': 'system', 'content': promt,},
                {'role': 'user', 'content': f"{answer1} {answer2} {answer3}"}]
        answer4, allToken4, allTokenPrice4= gpt.answer(' ',mess,)

        answer = answer4
        allToken = allToken1+allToken2+allToken3+allToken4
        allTokenPrice = allTokenPrice1+allTokenPrice2+allTokenPrice3+allTokenPrice4

        promt5URL = 'https://docs.google.com/document/d/1TPTa7s_VsbjMdaHw0k0EQrHecSnp8X5T-JoaOoGh53M/edit?usp=sharing'
        promt = gpt.load_prompt(promt5URL)
        promt = promt.replace('[analitict]', analitBTC)
        promt = promt.replace('[coin]', coin)
        promt = promt.replace('[exchangerate]', priceNow)
        # promt = promt.replace('[language]', 'Russian')

        mess = [{'role': 'system', 'content': promt,},
                {'role': 'user', 'content': f""}]
        #print(promt)
        answer5, allToken5, allTokenPrice5= gpt.answer(' ',mess,) 
        # prognozPrice, lowerPrice, upperPrice = prepare_prognoz(answer5)
        
        allTokenPrice += allTokenPrice5
        allToken += allToken5
        url = f'https://api.telegram.org/bot{TOKEN_BOT_FORECAST}/sendMessage'
        params = {
            'chat_id': -1002247551722,
            'text': answer5,
            'parse_mode': 'Markdown'  # или 'Markdown'
        }
        response = requests.post(url, params=params)
        return answer
    except Exception as e:
        print(e.__traceback__)
        pprint(e)
        logger.debug(f'{e=}')


if __name__ == '__main__':

    a=forecastText(0) 
    print(a)
    # send_message(2118909508,a,1)
    # print(a)
    
   