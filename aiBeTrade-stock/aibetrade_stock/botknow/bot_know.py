import os
import json
import openai
from pymongo import MongoClient
from datetime import datetime
from telethon import TelegramClient

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
vector_store_id = "vs_EgNRRvNbFrAiTSx9B9TOilhw"
# Создание или получение vector store
# try:
#     # Попытка создать новое хранилище
#     vector_store = client.beta.vector_stores.update(vector_store_id="vs_EgNRRvNbFrAiTSx9B9TOilhw",
#         name="edvil_school_store"
#     )
# except Exception as e:

def save_embeddings_to_json(embeddings_data):
    # Создаем директорию, если она не существует
    if not os.path.exists('embedding'):
        os.makedirs('embedding')
    
    # Создаем уникальное имя файла с временной меткой
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"embedding_{timestamp}.json"
    filepath = os.path.join('embedding', filename)
    
    # Сохраняем данные в JSON файл
    with open(filepath, 'w') as f:
        json.dump(embeddings_data, f)
    
    return filepath, filename

def add_messages_to_db(chat_data, bot=None, message=None):
    embeddings_data = []
    for record in chat_data:
        message_text = record.get('text', '')
        user = record.get('username', '')
        chat_id = str(record.get('chat_id', ''))
        chat_name = record.get('chat_name', '')
        user_id = str(record.get('user_id', ''))
        message_id = str(record.get('message_id', ''))
        timestamp = record.get('timestamp', '')

        if message_text:  # Проверяем, что сообщение не пустое
            try:
                # Создаем эмбеддинг для сообщения
                embedding_response = client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=message_text
                )
                embedding = embedding_response.data[0].embedding

                # Добавляем данные в список для JSON
                embeddings_data.append({
                    "id": f"{chat_id}_{message_id}",
                    "values": embedding,
                    "metadata": {
                        "text": message_text,
                        "chat_id": chat_id,
                        "user": user,
                        "chat_name": chat_name,
                        "user_id": user_id,
                        "message_id": message_id,
                        "timestamp": str(timestamp)
                    }
                })

            except Exception as e:
                print(f"Ошибка при создании эмбеддинга: {e}")

    try:
        # Сохраняем эмбеддинги в JSON файл
        filepath, filename = save_embeddings_to_json(embeddings_data)
        print(f"Эмбеддинги сохранены в файл: {filepath}")

        # Отправляем файл в Telegram

        # Загружаем файл в OpenAI
        with open(filepath, 'rb') as file:
            # Сначала создаем файл в OpenAI
            file_object = client.files.create(
                file=file,
                purpose="assistants"
            )
            
            # Затем добавляем файл в vector store
            vector_store_file = client.beta.vector_stores.files.create(
                vector_store_id=vector_store_id,
                file_id=file_object.id
            )
        
        if bot and message:
            bot.send_document(
                message.chat.id,
                file_object.id,
                caption=f"Файл эмбеддингов: {filename}"
            )
        return "Все сообщения успешно обработаны и загружены в vector store."
    except Exception as e:
        error_message = f"Ошибка при сохранении или загрузке файла: {e}"
        print(error_message)
        if bot and message:
            bot.reply_to(message, error_message)
        return error_message

def search_messages(query, n_results=5, bot=None, message=None):
    try:
        # Создаем эмбеддинг для запроса
        bot.reply_to(message, f"Поиск релевантных сообщений: {query}")
        embedding_response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=query
        )
        query_embedding = embedding_response.data[0].embedding
        bot.reply_to(message, f"Эмбеддинг запроса: {query_embedding}")
        # Поиск похожих сообщений
        results = vector_store.query(
            query_vector=query_embedding,
            n_results=n_results
        )
        bot.reply_to(message, f"Результаты поиска: {results}")
        return results
    except Exception as e:
        error_message = f"Ошибка при поиске сообщений: {e}"
        print(error_message)
        if bot and message:
            bot.reply_to(message, error_message)
        return error_message

def generate_essay(context, bot, message, query=None):
    try:
        # Инициализируем переменную для хранения полного ответа
        full_response = ""
        
        # Нужно разбить на несколько запросов если context больше 3000 символов
        if len(context) > 3000:
            chunks = [context[i:i+3000] for i in range(0, len(context), 3000)]
            for chunk in chunks:
                prompt = f"На основе следующего контекста сформируй краткое эссе:\n{chunk}"
                if query is not None:
                    prompt += f"\nЗапрос: {query}"

                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Ты помощник, который формирует эссе на основе данных. Возвращай только самое важное и смысловое из контекста. По сути это сублимированные мысли, которые можно использовать в качестве основы для дальнейшего развития маркетинга, идей по проекту, важных заметок и т.д. Твой ответ не должен содержать пересказывание полученного контектса, только твой анализ и выводы."},
                        {"role": "user", "content": prompt}
                    ]
                )
                # Добавляем текст ответа к полному ответу
                full_response += response.choices[0].message.content + "\n"                
        else:
            # Если контекст небольшой, отправляем его целиком
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
            full_response = response.choices[0].message.content
            
        if full_response:
            return full_response
        else:
            return "Не удалось сформировать эссе."
    except Exception as e:
        error_message = f"Ошибка при генерации эссе: {e}"
        print(error_message)
        if bot and message:
            bot.reply_to(message, error_message)
        return None

def chat_data_load(bot, message):
    try:
        # Получение данных из MongoDB
        chat_data = list(info_collection.find({}))
        if not chat_data:
            return "Нет данных для загрузки в базу данных."

        # Добавление сообщений в vector store
        result = add_messages_to_db(chat_data)
        bot.reply_to(message, result)

        # Генерация эссе на основе всех сообщений
        all_messages = " ".join([record.get('text', '') for record in chat_data if record.get('text')])
        if all_messages:
            essay = generate_essay(all_messages, bot, message)
            if essay:
                # Сохранение эссе в MongoDB
                info_collection.insert_one({
                    'text': essay,
                    'username': 'bot_essey',
                    'chat_id': 'system',
                    'chat_name': 'essay_generation',
                    'user_id': 'system',
                    'message_id': str(datetime.now().timestamp()),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'type': 'essay'
                })
                key = add_messages_to_db(essay, bot, message)
                print(key)
                return essay
            else:
                bot.reply_to(message, "Не удалось сгенерировать эссе.")
                return "Не удалось сгенерировать эссе."
        return result
    except Exception as e:
        bot.reply_to(message, f"Ошибка при загрузке данных: {e}")
        return f"Ошибка при загрузке данных: {e}"

def search_messages_by_query(query, bot=None, message=None):
    try:
        # Поиск релевантных сообщений
        search_results = search_messages(query, n_results=3)
        if not search_results:
            return "Не найдено релевантных сообщений."

        # Формирование контекста из найденных сообщений
        context = "\n".join([
            f"Сообщение: {result.metadata.get('text')}\n"
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
        error_message = f"Ошибка при поиске сообщений: {e}"
        print(error_message)
        if bot and message:
            bot.reply_to(message, error_message)
        return error_message

if __name__ == '__main__':
    result = chat_data_load(bot, message)
    print(result)

