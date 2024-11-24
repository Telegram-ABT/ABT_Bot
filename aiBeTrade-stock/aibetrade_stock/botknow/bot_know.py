import os
import telebot
from pymongo import MongoClient
import openai
import asyncio
import chromadb
from sentence_transformers import SentenceTransformer
from datetime import datetime

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


# Инициализация модели эмбеддингов
model = SentenceTransformer('all-MiniLM-L6-v2')  # Легкая и быстрая модель
# Инициализация ChromaDB
client = chromadb.Client()

# Имя коллекции
collection_name = "edvil_school"

# Проверка наличия коллекции
existing_collections = client.list_collections()
if collection_name not in existing_collections:
    collection_communication = client.create_collection(collection_name)
    print(f"Коллекция '{collection_name}' создана.")
else:
    collection_communication = client.get_collection(collection_name)
    print(f"Коллекция '{collection_name}' уже существует и будет использована.")


# Создаем функцию для генерации эмбеддингов
def create_embedding(text):
    return model.encode(text).tolist()


# Функция добавления сообщений в базу данных
def add_messages_to_db(chat_data):
    for record in chat_data:
        message = record.get('text', '')
        user = record.get('username', '')
        chat_id = record.get('chat_id', '')
        chat_name = record.get('chat_name', '')
        user_id = record.get('user_id', '')
        message_id = record.get('message_id', '')
        timestamp = record.get('timestamp', '')

        # Генерация эмбеддинга для сообщения
        embedding = create_embedding(message)

        # Добавление сообщения в коллекцию
        collection_communication.add(
            documents=[message],
            metadatas=[{"chat_id": chat_id, "user": user, "chat_name": chat_name, "user_id": user_id, "message_id": message_id, "timestamp": timestamp}],
            ids=[f"{chat_id}_{timestamp}"],
            embeddings=[embedding]
        )
    print("Все сообщения успешно добавлены в базу данных.")

# Функция поиска релевантных сообщений
def search_messages(query, n_results=5):
    query_embedding = create_embedding(query)
    results = collection_communication.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )
    return results

# Функция формирования эссе с помощью GPT
def generate_essay(context,query=None):
    prompt = f"На основе следующего контекста сформируй краткое эссе:\n{context}"
    if query is not None:
        prompt += f"\nЗапрос: {query}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Ты помощник, который формирует эссе на основе данных."},
            {"role": "user", "content": prompt}
        ]
    )
    return response["choices"][0]["message"]["content"]

# def chat_data_load():
#     chat_data = info_collection.find({})

#     return chat_data
# Имитация данных из чатов
def chat_data_load():
    chat_data = info_collection.find({})
    if chat_data is None:
        raise ValueError("Запись с ключом 'chat_data' не найдена в коллекции 'bot_secrtary_info'.") 
    else:
        add_messages_to_db(chat_data)
        generate_essay_by_query(chat_data)
        return "Сообщения успешно добавлены в базу данных."


# Поиск сообщений по запросу

def search_messages_by_query(query):
    search_results = search_messages(query, n_results=3)
    text_out = None
    print("\nРелевантные сообщения:")
    for doc, meta in zip(search_results['documents'], search_results['metadatas']):
        text_out += (f"Сообщение: {doc}, Пользователь: {meta['user']}, Время: {meta['timestamp']}")

    if text_out is None:
        return "Не найдено релевантных сообщений."
    else:
        essay = generate_essay(text_out,query)
        if essay is None:
            return "Не удалось сформировать эссе."
        else:
            return essay


def generate_essay_by_query(query):
    # Генерация эссе на основе найденной информации
    if query:
        essay = generate_essay(query)
        # Создаем структуру данных для add_messages_to_db
        essay_data = [{
            'text': essay,
            'username': 'bot',
            'chat_id': 'system',
            'chat_name': 'essay_generation',
            'user_id': 'system',
            'message_id': str(datetime.now().timestamp()),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }]
        add_messages_to_db(essay_data)
        return essay
    return "Не удалось найти релевантные сообщения для запроса."

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)

