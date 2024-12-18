from fastapi import FastAPI, HTTPException,Form,Depends
import requests
from pprint import pprint
import os
from dotenv import load_dotenv
# from fastapi.security import OAuth2PasswordBearer
load_dotenv()

from typing import Annotated
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel,Field
from datetime import datetime
from pprint import pformat, pprint
from chromaDBwork import add_to_collection, query, prepare_query_chromadb
import json
from tqdm import tqdm      
# from fastapi import FastAPI, 
# TOKEN_BOT = os.getenv('TOKEN_BOT_EVENT')

app = FastAPI(debug=False)
load_dotenv()
PORT1 = os.getenv('PORT_VECTOR_DB_WORK')
HOST = os.getenv('HOST')


app = FastAPI(
    title="STRANA System API",
    description="Vector DB API\nЛоги можно посмотреть по пути /logs\nОчистить логи можно по пути /clear_logs\n",
    version="1.0"
)
app.mount("/static", StaticFiles(directory="static/"), name="static")
templates = Jinja2Templates(directory="templates")
logs = []


def load_from_file(filename):
    """Загружает данные из файла в формате JSON."""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)  
    
testDict= load_from_file('nntcapital.bot_secrtary_info.json')
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
# @app.get("/items/")
# async def read_items(token: Annotated[str, Depends(oauth2_scheme)]):
#     return {"token": token}
pprint(testDict)
i=0
print('Создание базы')
for message in tqdm(testDict):


    # for key, value in tqdm(message.items()):
        
        # text+=f'{key}: {value}'
    title=message['text']
    # chatID=message['']

    # pprint(key)
        # key=key['text']
    meta=message.copy()
    meta['id']=i
    try:
        meta['chat_id']=meta['chat_id'].get('$numberLong')
    except: 
        meta['chat_id']

    try:    
        meta['_id']=meta['_id'].get('$oid')
    except:
        meta['_id']
    try:
        meta['user_id']=meta['user_id'].get('$numberLong')
    except:
        meta['user_id']

    if meta['chat_name']==None:
        meta['chat_name']='None'
    add_to_collection(text=title,
        meta=meta)  
    i+=1



@app.post("/create_or_add_value_in_collection")
async def create_or_add_value_in_collection(text:str, meta:dict=None) -> None:
    
    add_to_collection(text, meta)
    
@app.post("/query_collection")
async def query_collection(text:str, 
                        filter:dict, 
                        needDistance:bool=False, 
                        result:int=2) -> list | dict:
    
    if filter=={}: filter = None
    queryAnswer=query(text=text, filter1=filter, 
                        result=result)
    if needDistance:
        queryAnswer=prepare_query_chromadb(queryAnswer)

    return queryAnswer 


#работа с логами

def log_counts_by_level(logs: list) -> dict:
    counts = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0}
    for log in logs:
        counts[log['level']] += 1
    return counts

def log_counts_by_minute(logs: list) -> dict:
    counts_by_minute = {}
    for log in logs:
        timestamp_minute = log['timestamp'][:16]  # Обрезаем до минут
        if timestamp_minute in counts_by_minute:
            counts_by_minute[timestamp_minute][log['level']] += 1
        else:
            counts_by_minute[timestamp_minute] = {'DEBUG': 0, 'INFO': 0, 'WARNING': 0, 'ERROR': 0}
            counts_by_minute[timestamp_minute][log['level']] += 1
    return counts_by_minute

@app.post("/logs")
async def add_log(log: Request):
    global logs

    # pprint(log.__dict__)
    json = await log.json()
    log_entry=json.get('log_entry')
    log_level = json.get('log_level')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    if len(logs) >= 100:
        logs.pop(0)
    logs.append({'timestamp': timestamp, 'level': log_level, 'message': log_entry})
    return {"message": "Лог записан!"}

@app.get("/logs", response_class=HTMLResponse)
async def view_logs(request: Request):
    global logs
    for log in logs:
        if isinstance(log['message'], dict) or isinstance(log['message'], list):
            log['message'] = pformat(log['message'])

    logs.reverse()
    counts_log = log_counts_by_level(logs)
    counts_log = log_counts_by_minute(logs)
    pprint(counts_log)
    return templates.TemplateResponse("index.html", {"request": request, "logs": logs, "log_counts": counts_log})

@app.post("/clear_logs")
async def clear_logs():
    global logs
    logs.clear()
    return {"message": "Логи очищены!"}

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=int(6000))

