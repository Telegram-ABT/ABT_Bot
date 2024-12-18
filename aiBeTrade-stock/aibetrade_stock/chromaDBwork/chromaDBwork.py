
import chromadb 
from pprint import pprint
import random
import openai

from openai import OpenAI

# Create a ChromaDB client
client = chromadb.Client()
import os
# Create a collection
from chromadb.utils import embedding_functions
# collection = client.create_collection("sample_collection")
# sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
# Инициализация клиента OpenAI
client_openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create a ChromaDB client
client = chromadb.Client()

# Create a collection


def openai_embedding(text: str):
    """Get embeddings from OpenAI for the given text."""
    response = client_openai.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return [data.embedding for data in response.data]
# collection = client.get_or_create_collection(name="my_collection")

collection = client.get_or_create_collection(name="my_collection")


def add_to_collection(text:str, meta:dict, collectionName:str="my_collection"):
    """Создает/подключается к колекции и добавляет в нее новые данные text и meta(должен быть ключь id обязательно) """
    val = openai_embedding(text)
    collection = client.get_or_create_collection(name=collectionName)
    pprint(meta)
    try:
        ID=str(meta['id'])
    
    except:
        ID=str(random.randint(1,10000000))

    # meta['id']=ID
    collection.add(
        embeddings=val,
        metadatas=[meta],
        ids=[ID]
        # ids=[str(random.randint(1,10000))]
    )


def query(text, filter1:dict=None, result:int=2, collectionName:str="my_collection"):
    """фильтр работает по принципу filter={'date':date} и это будет and для всех ключей"""
    
    val = openai_embedding(text)
    collection = client.get_or_create_collection(name=collectionName)

    # is None не работает
    try:
        len(filter1)>1
    except Exception as e:
        results = collection.query(
            query_embeddings=val,
            n_results=result,)
        return results
    
    print(f'{filter1=}')
    if len(filter1)>1:
        filt={'$and':[]}
        for key, value in filter1.items():
            filt['$and'].append({key: value})        
    else:
        filt=filter1


    results = collection.query(
        query_embeddings=val,
        n_results=result,
        # where={"metadata_field": "is_equal_to_this"}, # optional filter по методанным
        where=filt, # optional filter по методанным
        # where_document={"$contains":"search_string"}  # optional filter
    )
    return results
                      
def prepare_query_chromadb(dict1:dict)->list[dict]:
    """переводит ответ от базы просто в удобный формат"""
    allText=''
    dic=[]
    metas=dict1['metadatas'][0]
    distance=dict1['distances'][0]
    for event, distance1 in zip(metas, distance):
        # text=event['url']

        distance=distance1
        dic.append({'text':event['title'],
                    'distance':distance, 
                    'title':event['title'],
                    # 'theme':event['topic'],
                    # 'themeSearch':event['themeSearch'],
                    # 'hashtags':event['hashtags'],
                    'id':event['id']})
        # pprint(dic)
        # allText+=f"{event['text']}\n\n"
    return dic

def delete_collection(collectionName:str="my_collection"):
    client.delete_collection(collectionName)

# Query the collection for events on Thursday
# results = collection.query(
#     query_texts=["что в пятницу"],
#     n_results=1
# )
# print(results)
# Print the results
# for result in results:



