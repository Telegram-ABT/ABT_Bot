import os
import telebot
from pymongo import MongoClient
import openai
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment
from io import BytesIO
import json

# Настройки
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
VOSK_MODEL_PATH = os.getenv('VOSK_MODEL_PATH', 'vosk-model-small-ru-0.22')

# Проверка наличия необходимых переменных окружения
if not all([TELEGRAM_BOT_TOKEN, MONGO_URI, OPENAI_API_KEY, VOSK_MODEL_PATH]):
    raise ValueError("Пожалуйста, установите переменные окружения: TELEGRAM_BOT_TOKEN, MONGO_URI, OPENAI_API_KEY, VOSK_MODEL_PATH")

# Инициализация клиентов
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["nntcapital"]
info_collection = db['bot_secrtary_info']
openai.api_key = info_collection.find_one({"key": "bot_key"})["value"]

# Загрузка модели Vosk
if not os.path.exists(VOSK_MODEL_PATH):
    raise ValueError(f"Модель Vosk не найдена по пути: {VOSK_MODEL_PATH}")
vosk_model = Model(VOSK_MODEL_PATH)

# Функция для распознавания речи из голосовых сообщений
def recognize_speech(voice_file):
    audio = AudioSegment.from_file(BytesIO(voice_file), format="ogg")
    audio = audio.set_channels(1).set_frame_rate(16000)
    recognizer = KaldiRecognizer(vosk_model, 16000)
    buffer = BytesIO()
    audio.export(buffer, format="wav")
    buffer.seek(0)
    while True:
        data = buffer.read(4000)
        if len(data) == 0:
            break
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            return result.get('text', '')
    final_result = json.loads(recognizer.FinalResult())
    return final_result.get('text', '')

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    # Сохранение сообщения в базу данных
    info_collection.insert_one({
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'text': message.text,
        'timestamp': message.date
    })
    # Проверка на команду #bot_info
    if message.text.startswith('#bot_info'):
        query = message.text[len('#bot_info'):].strip()
        if query:
            response = get_info_response(query)
            bot.reply_to(message, response)
        else:
            bot.reply_to(message, "Пожалуйста, укажите запрос после #bot_info.")

# Обработчик голосовых сообщений
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    file_info = bot.get_file(message.voice.file_id)
    voice_file = bot.download_file(file_info.file_path)
    recognized_text = recognize_speech(voice_file)
    # Сохранение распознанного текста в базу данных
    info_collection.insert_one({
        'chat_id': message.chat.id,
        'chat_name': message.chat.title,
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'text': recognized_text,
        'timestamp': message.date
    })
    bot.reply_to(message, f"Распознанный текст: {recognized_text}")

# Функция для получения ответа от ChatGPT
def get_info_response(query):
    # Извлечение последних сообщений из базы данных для контекста
    recent_messages = list(info_collection.find().sort('timestamp', -1).limit(10))
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
