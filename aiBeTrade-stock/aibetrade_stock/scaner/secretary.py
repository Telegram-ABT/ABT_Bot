import os
import telebot
from pymongo import MongoClient
import openai
import asyncio

# Настройки
mongo_url = os.getenv('MONGO_URL_SERV')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Инициализация OpenAI клиента
client_openai = openai.OpenAI(api_key=OPENAI_API_KEY)

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
        'timestamp': message.date,
        'type': 'user_message'
    })
    # Проверка на команду #bot_info
    if message.text.startswith('@edvilschool_bot'):
        query = message.text[len('@edvilschool_bot'):].strip()
        if query:
            response = get_info_response(query, message.chat.id)
            info_collection.insert_one({
                'chat_id': message.chat.id,
                'chat_name': message.chat.title,
                'user_id': message.from_user.id,
                'username': message.from_user.username,
                'text': response,
                'timestamp': message.date,
                'type': '@edvilschool_bot'
            })
            bot.reply_to(message, response)
        else:
            bot.reply_to(message, "Пожалуйста, укажите запрос после #bot_info.")

# Функция для получения ответа от ChatGPT
def get_info_response(query, chat_id):
    # Извлечение последних сообщений из базы данных для контекста
    recent_messages = list(info_collection.find({'chat_id': chat_id}).sort('timestamp', -1).limit(10))
    context = "\n".join([msg['text'] for msg in recent_messages])
    text = f"Контекст:\n{context}\n\nВопрос: {query}\nОтвет:"
    prompt = ("Ты помощник для управления контентом в телеграмме. "
              "Ты можешь отвечать на вопросы и помогать пользователям отвечая на их вопросы. "
              "Группы телеграм соданы для поддержки общения команды разработчиков Игры Roblox Edvil shcool. "
              "Тебе передается контент и вопрос пользователя. "
              "Ты должен ответить на вопрос пользователя исходя из контента.")
    response = send_to_chatgpt(prompt, text)
    return response
    

def send_to_chatgpt(prompt, text):
    try:
        message = f"Отправка в ChatGPT: Промт: {prompt}, Текст: {text}"
        print(message)
        response = client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ]
        )
        gpt_response = response.choices[0].message.content.strip()
        return gpt_response
    except Exception as e:
        message = f"Ошибка при отправке запроса в ChatGPT: {e}"
        return message

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
