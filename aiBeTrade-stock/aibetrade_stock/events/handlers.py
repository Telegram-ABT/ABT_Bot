import asyncio
from aiogram import types, F, Router, html, Bot
from aiogram.types import (Message, CallbackQuery,
                           InputFile, FSInputFile,
                            MessageEntity, InputMediaDocument,
                            InputMediaPhoto, InputMediaVideo, Document)
from aiogram.filters import Command, StateFilter,ChatMemberUpdatedFilter
from aiogram.types.message import ContentType
from pprint import pprint
from aiogram.fsm.context import FSMContext
from typing import Any, Dict
from aiogram.types import (
    Message
)
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER

from aiogram.types import ChatMemberUpdated

from dotenv import load_dotenv
import os


from loguru import logger



load_dotenv()
TOKEN = os.getenv('TOKEN_BOT_EVENT')
# PAYMENTS_TOKEN = os.getenv('PAYMENTS_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK')
SECRECT_KEY = os.getenv('SECRET_CHAT')

# sql = Ydb()

router = Router()

bot = Bot(token=TOKEN,)

import requests
import hashlib
import base64
import json
import hmac
import aiohttp
import time

# import loguru
from loguru import logger
logger.add("logs/file_{time}.log",format="{time} - {level} - {message}", rotation="100 MB", retention="10 days", level="DEBUG")
# Define the secret key and other required information

REQUESTS=0
REQUESTS_PER_SECOND = 50  # Максимальное количество запросов в секунду
TOTAL_TIME = 0  # Общее время выполнения запросов
TOTAL_REQUESTS = 0  # Общее количество выполненных запросов
TIMEOUT_SECONDS = 5  # Установите желаемое время таймаута в секундах
# Создание семафора для ограничения количества запросов
semaphore = asyncio.Semaphore(REQUESTS_PER_SECOND)

# async with semaphore:
    # await asyncio.sleep(1 / REQUESTS_PER_SECOND)  # Задержка перед отправкой запроса
NEED_CHATS=[-1002118909508,
-1001609461642,
-1001967803227,
-1001609461642,
-1001517527759,
-1001657532978,
-1002242862285,
-1002247551722,
-1002231035352,
-1002163616957,
-1002185622410,
# -1001642718580,
# -1001918899816,
-1002161095631,
-1002483834652,
-1002415281592,
-1001929624291]




async def request_AiBeTrade(body, webhook: str = WEBHOOK_URL):
    global REQUESTS, TOTAL_TIME, TOTAL_REQUESTS

    REQUESTS+=1
    print(f'IN-{REQUESTS=}')
    start_time = time.time()  # Начало отсчета времени
    async with semaphore:  # Ограничение на количество одновременно выполняемых запросов
        # await asyncio.sleep(1 / REQUESTS_PER_SECOND)  # Задержка перед отправкой запроса
        
        secret_key = SECRECT_KEY

        # Преобразование тела в JSON-строку
        body_json = json.dumps(body)
        total_params = body_json.encode('utf-8')
        secret_key = secret_key.encode('utf-8')
        
        # Создание подписи
        signature = hmac.new(secret_key, total_params, hashlib.sha256).hexdigest()

        # Определение заголовков
        headers = {
            "Content-Type": "application/json",
            "X-Api-Signature-Sha256": signature
        }

        # Отправка POST-запроса
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)  # Установка таймаута
                async with session.post(webhook, headers=headers, data=body_json, timeout=timeout) as response:
                    response_text = await response.text()
                    if response.status == 200:
                        logger.debug(f'{webhook=}\n')
                        logger.debug(f'{headers=}\n')
                        logger.debug(f'{body_json=}\n')
                        logger.debug(f'{response_text=}\n')
                        logger.debug(f'{response.status=}\n')
                    # else:
                    #     logger.error(f'Error: {response.status}, {response_text}')
        except asyncio.TimeoutError:
            logger.error('Request timed out 1sec')  # Обработка таймаута
        except Exception as e:
            logger.error(f'Error: {e}')                 
        
        end_time = time.time()  # Конец отсчета времени
        elapsed_time = end_time - start_time  # Время выполнения запроса
        TOTAL_TIME += elapsed_time
        TOTAL_REQUESTS += 1
        
        # Вычисление среднего времени выполнения
        average_time = TOTAL_TIME / TOTAL_REQUESTS if TOTAL_REQUESTS > 0 else 0
        print(f'Average execution time: {average_time:.4f} seconds')

        REQUESTS-=1
        print(f'OUT-{REQUESTS=}')

@router.message(Command("help"))
async def help_handler(msg: Message, state: FSMContext):
    mess="/start - начало работы"
    await msg.answer(mess)
    return 0

@router.message_reaction()
async def message_reaction(msg: Message):
    pprint(msg)
    return 0

#Обработка калбеков
@router.callback_query()
async def message(msg: CallbackQuery):
    pprint(msg.message.message_id)
    userID = msg.from_user.id
    await msg.answer()
    callData = msg.data
    # pprint(callData)
    logger.debug(f'{callData=}')

           
    return 0



@router.chat_boost()
async def chat_boost_handler(chat_boost: types.ChatBoostUpdated) -> Any: 
    if chat_boost.chat.id not in NEED_CHATS:
        return 0
    print(f'{"booost":_^34}')
    pprint(chat_boost.__dict__)
    print(f'{"chat":_^34}')
    pprint(chat_boost.chat.__dict__)

    userID=chat_boost.boost.source.user.id
    chatID=chat_boost.chat.id
    print(f"{chatID=}")
    print(f"{userID=}")

    task_code = f"boost{chatID}"
    action = True
    body={
        "code": task_code,
        "userId": userID,
        "action": action
    }
    pprint(body)
    await request_AiBeTrade(body)
    pass

@router.removed_chat_boost()
async def removed_chat_boost_handler(chat_boost: types.ChatBoostRemoved) -> Any: 
    # pprint(chat_boost.__dict__)
    # pprint(chat_boost.chat.__dict__)
    if chat_boost.chat.id not in NEED_CHATS:
        return 0
    print(f'{"booost":_^34}')
    pprint(chat_boost.__dict__)
    print(f'{"chat":_^34}')
    pprint(chat_boost.chat.__dict__)

    # pprint(chat_boost.source.__dict__)
    userID=chat_boost.source.user.id
    chatID=chat_boost.chat.id
    print(f"{chatID=}")
    print(f"{userID=}")

    task_code = f"boost{chatID}"
    action = False
    body={
        "code": task_code,
        "userId": userID,
        "action": action
    }
    pprint(body)
    await request_AiBeTrade(body)
    pass

@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def on_user_leave(event: ChatMemberUpdated):
    if event.chat.id not in NEED_CHATS:
        return 0
    print('on_user_leave')
    # pprint(event)
    # print(event.from_user.id)
    userID=event.from_user.id
    chatID=event.chat.id
    # print(chatID)
    task_code = f"sub{chatID}"
    action = False
    body={
        "code": task_code,
        "userId": userID,
        "action": action
    }
    # pprint(body)
    await request_AiBeTrade(body)

@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_user_join(event: ChatMemberUpdated):
    # await message(event.message, event.state)  
    if event.chat.id not in NEED_CHATS:
        return 0
    print('on_user_join')
    # pprint(event)
    # print(event.from_user.id)
    userID=event.from_user.id
    chatID=event.chat.id
    task_code = f"sub{chatID}"
    action = True
    body={
        "code": task_code,
        "userId": userID,
        "action": action
    }
    # pprint(body)
    await request_AiBeTrade(body)
    
    # print(chatID)
    pass

async def delete_and_send_message(msg:Message, text='You have violated the rules of this chat.  Message deleted. If you violate it again, you will be blocked.'):
    """удаление сообщения и отправка нового сообщения"""
    await msg.delete()
    new_msg = await msg.answer(text,)
    # делайем слип (асинхронно)
    await asyncio.sleep(5)
    # на всякий случай проверяем есть ли еще сообщение
    try:
        print('удалили')
        await new_msg.delete()
    except Exception as e:
        pprint(e)
        pass
    pass

# aibetradecombot/app?startapp

# office.aibetrade.com/?ref

def check_ref(msg:Message):
    """Проверка на реферальную ссылку true если его нету"""
    text=msg.text
    # Проверяем наличие http или t.me/
    if 'http' in text or 't.me/' in text or 'bot' in text:
        # Проверяем отсутствие aibetrade
        if 'aibetrade' not in text:
            return True
        else:
            return False
    return False

def chek_http(msg):
    text=msg.text
    if text in 'http':
        return True
    return False

    

    pass
#Обработка сообщений
@router.message()
async def message(msg: Message, state: FSMContext):
    # pprint(msg.__dict__)
    # 241 реф ссылки #240
    userID = msg.from_user.id
    # print(msg.chat.id)
    print(f"{msg.chat.id=}")
    print(f'{userID=}')
    
    
    # if msg.chat.id != -1002118909508:
    #     return 0
    if msg.chat.id not in [-1002118909508,-1002242862285,-1002231035352,-1002163616957]:
        return 0
    
    thereadID=msg.message_thread_id
   
    

    #336464992 I OWN ZERGO
    if userID in [327475194,336464992, 1087968824]: return 0
    
    
    if check_ref(msg):
        print(f"{'попали в чек':_^34}")
        print(f"{msg.chat.id=}")
        print(f'{userID=}')

        # if check_ref(msg) == False: await 
        if thereadID==240 or thereadID==241:            
            # print('попали')
            await delete_and_send_message(msg)    
            return 0
        else:
            # print('не попали')
            if msg.chat.id == -1002118909508:
                await delete_and_send_message(msg, text='You have violated the rules of this group.  Referral links can be published in the "Referral links" threads')
            else:
                await delete_and_send_message(msg)
            return 0
    else:
        
        # print('попали')
        # await delete_and_send_message(msg)
        return 0

    print(thereadID)

    pass



if __name__ == '__main__':
    # body={
    #     "code": 'boost-1001609461642',
    #     "userId": 327475194,
    #     "action": True  
    # }
    # pprint(body)
    # request_AiBeTrade(body)

    pass
