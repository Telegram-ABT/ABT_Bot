import os
import openai
from pymongo import MongoClient
from datetime import datetime

# Настройки
mongo_url = os.getenv('MONGO_URL_SERV')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Инициализация клиентов
mongo_client = MongoClient(mongo_url)
db = mongo_client["nntcapital"]
info_collection = db['bot_secrtary_info']
info_settings = db['bot_secrtary_settings']

# Инициализация OpenAI клиента
client = openai.Client(api_key=OPENAI_API_KEY)

# Создание или получение vector store
try:
    # Попытка создать новое хранилище
    vector_store = client.beta.vector_stores.create(
        name="edvil_school_store"
    )
except Exception as e:
    print(f"Ошибка при создании vector store: {e}")
    try:
        # Если хранилище уже существует, получаем его
        vector_stores = client.beta.vector_stores.list()
        vector_store = next((store for store in vector_stores.data if store.name == "edvil_school_store"), None)
        if not vector_store:
            raise Exception("Не удалось получить существующий vector store")
    except Exception as e:
        print(f"Ошибка при получении vector store: {e}")
        raise Exception("Не удалось создать или получить vector store")

def add_messages_to_db(chat_data):
    for record in chat_data:
        message = record.get('text', '')
        user = record.get('username', '')
        chat_id = str(record.get('chat_id', ''))
        chat_name = record.get('chat_name', '')
        user_id = str(record.get('user_id', ''))
        message_id = str(record.get('message_id', ''))
        timestamp = record.get('timestamp', '')

        if message:  # Проверяем, что сообщение не пустое
            try:
                # Добавление сообщения в vector store
                vector_store.add_texts(
                    texts=[message],
                    metadata=[{
                        "chat_id": chat_id,
                        "user": user,
                        "chat_name": chat_name,
                        "user_id": user_id,
                        "message_id": message_id,
                        "timestamp": str(timestamp)
                    }]
                )
            except Exception as e:
                print(f"Ошибка при добавлении сообщения в vector store: {e}")

    return "Все сообщения успешно добавлены в базу данных."

def search_messages(query, n_results=5):
    try:
        # Поиск похожих сообщений
        results = vector_store.query(
            query=query,
            n_results=n_results
        )
        return results
    except Exception as e:
        print(f"Ошибка при поиске сообщений: {e}")
        return None

def generate_essay(context, query=None):
    try:
        prompt = f"На основе следующего контекста сформируй краткое эссе:\n{context}"
        if query is not None:
            prompt += f"\nЗапрос: {query}"

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты помощник, который формирует эссе на основе данных."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Ошибка при генерации эссе: {e}")
        return None

def chat_data_load():
    try:
        # Получение данных из MongoDB
        chat_data = list(info_collection.find({}))
        if not chat_data:
            return "Нет данных для загрузки в базу данных."

        # Добавление сообщений в vector store
        result = add_messages_to_db(chat_data)

        # Генерация эссе на основе всех сообщений
        all_messages = " ".join([record.get('text', '') for record in chat_data if record.get('text')])
        if all_messages:
            essay = generate_essay(all_messages)
            if essay:
                # Сохранение эссе в MongoDB
                info_collection.insert_one({
                    'text': essay,
                    'username': 'bot',
                    'chat_id': 'system',
                    'chat_name': 'essay_generation',
                    'user_id': 'system',
                    'message_id': str(datetime.now().timestamp()),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'essay'
                })
                return essay
            else:
                return "Не удалось сгенерировать эссе."
        return result
    except Exception as e:
        return f"Ошибка при загрузке данных: {e}"

def search_messages_by_query(query):
    try:
        # Поиск релевантных сообщений
        search_results = search_messages(query, n_results=3)
        if not search_results:
            return "Не найдено релевантных сообщений."

        # Формирование контекста из найденных сообщений
        context = "\n".join([
            f"Сообщение: {result.text}\n"
            f"Пользователь: {result.metadata.get('user')}\n"
            f"Время: {result.metadata.get('timestamp')}\n"
            for result in search_results.matches
        ])

        # Генерация эссе на основе найденных сообщений
        essay = generate_essay(context, query)
        if essay:
            return essay
        else:
            return "Не удалось сформировать эссе."
    except Exception as e:
        return f"Ошибка при поиске сообщений: {e}"

if __name__ == '__main__':
    result = chat_data_load()
    print(result)

