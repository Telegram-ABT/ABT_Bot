import os
import telebot
from pymongo import MongoClient
import openai
import base64

# Настройки
mongo_url = os.getenv('MONGO_URL_SERV')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Инициализация OpenAI клиента
client_openai = openai.OpenAI(api_key=OPENAI_API_KEY)

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

# Функция для кодирования изображения в base64
def encode_image(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

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
        'message_id': message.message_id,
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
                'message_id': message.message_id,
                'type': '@edvilschool_bot'
            })
            bot.reply_to(message, response)
        else:
            bot.reply_to(message, "Пожал��йста, укажите запрос после #bot_info.")

# Обработчик изображений
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    # Получение информации о файле
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    # Создание директории для сохранения изображений, если она не существует
    directory = f"pic/{message.chat.id}"
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Формирование имени файла
    file_name = f"{message.chat.id}_{message.from_user.id}_{message.message_id}.jpg"
    file_path = os.path.join(directory, file_name)

    # Сохранение файла
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)

    # Кодирование изображения в base64
    base64_image = encode_image(file_path)

    # Сохранение информации в базу данных
    info_collection.insert_one({
        'chat_id': message.chat.id,
        'chat_name': message.chat.title,
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'text': message.caption if message.caption else "",  # Сохраняем текст, если он есть
        'timestamp': message.date,
        'message_id': message.message_id,
        'type': 'photo_message',
        'photo_link': file_path  # Сохраняем путь к изображению
    })

    # Проверка на упоминание @edvilschool_bot
    if message.caption and '@edvilschool_bot' in message.caption:
        query = message.caption.split('@edvilschool_bot', 1)[1].strip()
        prompt = "Проанализируй изображение и ответь на вопрос: " + query
        response = send_to_chatgpt_with_image(prompt, base64_image)
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, f"Изображение сохранено как {file_name}")

    # Удаление файла после обработки
    os.remove(file_path)

def send_to_chatgpt_with_image(promt:str, base64_image:str):
    try:
        response = client_openai.ChatCompletion.create(
          model="gpt-4-vision-preview",
          messages=[
              {
                  "role": "user",
                  "content": [
                      {"type": "text", "text": promt},
                      {
                          "type": "image_url",
                          "image_url": {
                             'url': f"data:image/jpeg;base64,{base64_image}"
                          },
                      },
                  ],
              }
          ],
    )

        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка при отправке запроса в ChatGPT: {e}"


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
        response = client_openai.ChatCompletion.create(
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
