import time
import requests
import json
import logging
import openai
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Установите ваш токен бота Telegram и id группы
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_GROUP_ID = "@abtbitxx"
TELEGRAM_GROUP_ID_RU = "@abtbit"

URL = os.getenv('URL')
URL_BOT = 'https://api.telegram.org/bot'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# Создаем логгер
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_news():
    try:
        response = requests.get(URL)
        response.raise_for_status()
        news_data = response.json()
        logging.info("Данные успешно получены с URL")
        return news_data["data"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении данных: {e}")
        return []


def send_news_to_telegram(news_item):
  
    image_url = news_item.get("image_url", "")
    title = news_item.get("title", "")
    text = news_item.get("text", "")
    sentiment = news_item.get("sentiment", "")
    source_name = news_item.get("source_name", "")
    news_url = news_item.get("news_url", "")

    sentiment_emoji = "⚪"  # Серый смайлик по умолчанию
    if sentiment == "Positive":
        sentiment_emoji = "🟢"  # Зеленый круг
    elif sentiment == "Negative":
        sentiment_emoji = "🔴"  # Красный круг

    message_text = f"<b>{title}</b>\n\n{text}\n\n{sentiment_emoji}\n\nSorce:<a href='{news_url}'>{source_name}</a>"
 
    logging.info("Пост в Telegram: " + message_text)
    
    try:
           requests.get(f'{URL_BOT}{TELEGRAM_BOT_TOKEN}/sendPhoto?chat_id={TELEGRAM_GROUP_ID}&photo={image_url}&parse_mode=HTML&caption={message_text}')
           logging.info("Пост успешно отправлен в Telegram")
           textGpt = gpt_chat("Русский", message_text)
        #    TextRU = textGpt.choices[0].message['content'].strip()


        #    response_json = json.loads(textGpt)
        #    TextRU = response_json["choices"][0]["message"]["content"]

           requests.get(f'{URL_BOT}{TELEGRAM_BOT_TOKEN}/sendPhoto?chat_id={TELEGRAM_GROUP_ID_RU}&photo={image_url}&parse_mode=HTML&caption={textGpt}')
           logging.info("Пост успешно отправлен в Telegram")
    except Exception as e:
        logging.error(f"Ошибка при отправке поста в Telegram: {e}")


def display_news_item(news_item):
    print("News Item:")
    print(f"Title: {news_item.get('title', '')}")
    print(f"Text: {news_item.get('text', '')}")
    print(f"Sentiment: {news_item.get('sentiment', '')}")
    print(f"Image URL: {news_item.get('image_url', '')}")
    print(f"Source name: {news_item.get('source_name', '')}")
    print(f"News url: {news_item.get('news_url', '')}")
  
    print("-" * 40)
    
def gpt_chat(prompt, text):
    client = OpenAI(api_key=OPENAI_API_KEY)
    # Инициализация клиента OpenAI
    prompt_text = "Переведи на "+prompt+" Не меняй в исходном тексте служебные символы и структуру HTML"
    try:
        # Отправляем запрос в GPT-чат
        response  = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt_text+": "+text,
        }
    ],
    model="gpt-3.5-turbo",
)

        # Возвращаем ответ от GPT-чата
        return response.choices[0].message.content
    
    except Exception as e:
        return f"Произошла ошибка: {e}"


def main():
    while True:
        logging.info("Начинаем новый цикл получения и отправки новостей")
        news_list = fetch_news()
        for news_item in news_list:
            # display_news_item(news_item)
            send_news_to_telegram(news_item)
        logging.info("Цикл завершен, ждем 60 мин до следующего запроса")
        time.sleep(3600)  # ждём 1 час

if __name__ == "__main__":
    main()