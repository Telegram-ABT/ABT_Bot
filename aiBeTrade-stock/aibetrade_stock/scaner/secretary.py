import os
import telebot
from pymongo import MongoClient
import openai

# Настройки
mongo_url = os.getenv('MONGO_URL_SERV')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Проверка наличия необходимых переменных окружения

# Инициализация клиентов
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
info_collection = db['bot_secrtary_info']
info_settings = db['bot_secrtary_settings']

# Получение ключа бота
key_bot_record = info_settings.find({})
if key_bot_record is None:
    raise ValueError("Запись с ключом 'bot_key' не найдена в коллекции 'bot_secrtary_settings'.")
key_bot = None
for record in key_bot_record:
    key_bot = record.get('bot_key')
if not key_bot:
    raise ValueError("Пожалуйста, установите переменные окружения: bot_key")

TELEGRAM_BOT_TOKEN = key_bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Сохранение сообщения в базу данных
    info_collection.insert_one({
        'chat_id': message.chat.id,
        'chat_name': message.chat.title,
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'text': message.text,
        'timestamp': message.date
    })
    # Проверка на команду #bot_info
    if message.text.startswith('#bot_info'):
        query = message.text[len('#bot_info'):].strip()
        if query:
            response = get_info_response(query, message.chat.id)
            bot.reply_to(message, response)
        else:
            bot.reply_to(message, "Пожалуйста, укажите запрос после #bot_info.")

# Функция для получения ответа от ChatGPT
def get_info_response(query, chat_id):
    # Извлечение последних сообщений из базы данных для контекста
    recent_messages = list(info_collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(10))
    context = "\n".join([msg['text'] for msg in recent_messages])
    prompt = f"Контекст:\n{context}\n\nВопрос: {query}\nОтвет:"
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7
        )
        return response.choices[0].text.strip()
    except Exception as e:
        return f"Ошибка при обращении к ChatGPT: {e}"

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
