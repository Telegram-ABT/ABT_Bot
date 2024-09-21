from datetime import datetime, timedelta
import os
import time
import random
import requests
from dotenv import load_dotenv
from chat import GPT
from binance import Client
from pprint import pprint

# Загрузка переменных окружения
load_dotenv()

# Инициализация переменных и объектов
gpt = GPT()
TOKEN_BOT_FORECAST = os.getenv('TOKEN_BOT_FORECAST')
STOCK_URL = os.getenv('STOCK_URL')
api_key = os.getenv('api_key_binance')
api_secret = os.getenv('api_secret_binance')
client = Client(api_key, api_secret)

coins = {
    'Bitcoin': 'BTCUSDT',
    'Ethereum': 'ETHUSDT',
    'Bnb': 'BNBUSDT',
    'Ripple': 'XRPUSDT',
    'Cardano': 'ADAUSDT',
    'Dogecoin': 'DOGEUSDT',
    'Solana': 'SOLUSDT',
    'Tron': 'TRXUSDT',
    'Polkadot': 'DOTUSDT',
    'Polygon': 'MATICUSDT'
}

def get_dates(day, pattern='%d/%m/%Y'):
    """Форматирует текущую и будущую дату."""
    current_date = datetime.now().strftime(pattern)
    future_date = (datetime.now() + timedelta(days=day)).strftime(pattern)
    return current_date, future_date

def date_now():
    """Возвращает текущую дату в формате '%Y-%m-%dT%H:00:00Z'."""
    patern = '%Y-%m-%dT%H:00:00'
    return datetime.now().strftime(patern) + 'Z'

def prepare_prognoz(text):
    """Извлекает прогнозные значения из текста."""
    import re
    pattern = r"\d+\.\d+"
    matches = re.findall(pattern, text)
    if len(matches) >= 3:
        prognozPrice, lowerPrice, upperPrice = matches[0], matches[1], matches[2]
    elif len(matches) == 2:
        prognozPrice, lowerPrice, upperPrice = matches[0], matches[1], 0
    else:
        prognozPrice, lowerPrice, upperPrice = matches[0], 0, 0
    return prognozPrice, lowerPrice, upperPrice

def get_BTC_analit_for(dayStart, coin):
    """Возвращает аналитику по BTC на заданное количество дней."""
    coin = coins[coin.title()]
    settings = {
        'Аналитика BTC на 5 дней': [Client.KLINE_INTERVAL_1DAY, '3 month ago UTC'],
        'Аналитика BTC на 15 дней': [Client.KLINE_INTERVAL_1DAY, '3 month ago UTC'],
        'Аналитика BTC на 30 дней': [Client.KLINE_INTERVAL_1WEEK, '2 year ago UTC'],
    }
    setting = settings.get(dayStart, [Client.KLINE_INTERVAL_1HOUR, '6 day ago UTC'])
    klines = client.get_historical_klines(coin, setting[0], setting[1])
    return prepare_list(klines)

def prepare_list(lst):
    """Преобразует данные свечей в удобочитаемый формат."""
    text = ''
    for i in lst:
        i[0] = timestamp_to_date(i[0])
        i[6] = timestamp_to_date(i[6])
        candle_dict = {
            'Open time': i[0], 'High': i[2], 'Low': i[3], 'Close': i[4], 
            'Volume': i[5], 'Close time': i[6], 'Quote asset volume': i[7], 'Number of trades': i[8]
        }
        text += f"\n& {candle_dict['Open time']}; {float(candle_dict['High'])}; {float(candle_dict['Low'])}; {float(candle_dict['Close'])}; {round(float(candle_dict['Volume']))}; {candle_dict['Close time']}; {round(float(candle_dict['Quote asset volume']))}; {round(float(candle_dict['Number of trades']))}"
    return text

def timestamp_to_date(timestamp):
    """Конвертирует метку времени в строку даты."""
    dt_object = datetime.fromtimestamp(int(timestamp) / 1000)
    return dt_object.strftime("%d/%m/%y")

def get_price_now(coin):
    """Возвращает текущую цену для указанного актива."""
    coin = coins[coin.title()]
    priceNow = client.get_symbol_ticker(symbol=coin)
    return float(priceNow['price'])

def forecastText(day, coin='Bitcoin'):
    """Генерирует текст прогноза с использованием данных аналитики и GPT."""
    dateNow = date_now()
    analitBTC = get_BTC_analit_for(day, coin)
    current, future = get_dates(day)
    priceNow = str(get_price_now(coin))

    print(f"Текущая дата: {current}")
    print(f"Дата через {day} дней: {future}")

    promtURL = [
        'https://docs.google.com/document/d/1_Ft4sDJJpGdBX8k2Et-OBIUtvO0TSuw8ZSjbv5r7H7I/edit?usp=sharing',
        'https://docs.google.com/document/d/1kvtS8FDYQ7Mg0QTuIYLUzfzPzIwNtNAy8nVHTDcmH1A/edit?usp=sharing',
        'https://docs.google.com/document/d/15nj87WI9Ud3EGgmp0JM0AZdQVQGPgN3ly-zjWCEUsB0/edit?usp=sharing',
        'https://docs.google.com/document/d/17hsm51kQGnhXgU7LkFkCGxsIBY82FPefowN8GcGIa6U/edit?usp=sharing',
        'https://docs.google.com/document/d/1cqDETdeSLj2vX8nBzWFbNV4jAl61oz_nGwL16EM-ZIM/edit?usp=sharing',
        'https://docs.google.com/document/d/1TPTa7s_VsbjMdaHw0k0EQrHecSnp8X5T-JoaOoGh53M/edit?usp=sharing'
    ]

    try:
        answers = []
        allToken = 0
        allTokenPrice = 0
        for i in range(len(promtURL) - 1):
            promt = gpt.load_prompt(promtURL[i])
            promt = promt.replace('[analitict]', analitBTC).replace('[nextDate]', str(day))
            promt = promt.replace('[coin]', coin).replace('[nowDate]', future)
            promt = promt.replace('[exchangerate]', priceNow)
            mess = [{'role': 'system', 'content': promt}, {'role': 'user', 'content': ' '}]
            answer, token, tokenPrice = gpt.answer(' ', mess)
            answers.append(answer)
            allToken += token
            allTokenPrice += tokenPrice

        promt = gpt.load_prompt(promtURL[-1])
        promt = promt.replace('[analitict]', analitBTC).replace('[coin]', coin)
        promt = promt.replace('[exchangerate]', priceNow)
        mess = [{'role': 'system', 'content': promt}, {'role': 'user', 'content': ' '.join(answers)}]
        final_answer, token, tokenPrice = gpt.answer(' ', mess)
        allToken += token
        allTokenPrice += tokenPrice

        url = f'https://api.telegram.org/bot{TOKEN_BOT_FORECAST}/sendMessage'
        params = {'chat_id': -1002247551722, 'text': final_answer, 'parse_mode': 'Markdown'}
        response = requests.post(url, params=params)
        return final_answer
    except Exception as e:
        pprint(e)

if __name__ == '__main__':
    result = forecastText(0) 
    print(result)
