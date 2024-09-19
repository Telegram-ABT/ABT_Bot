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
from aiogram.fsm.state import State, StatesGroup
from typing import Any, Dict
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER

from aiogram.types import ChatMemberUpdated
# from aiogram.dispatcher.filters import ChatMemberUpdatedFilter
# from helper import (get_all_user_list, get_dates, 
#                     timestamp_to_date, time_epoch,
#                     get_future_events, prepare_message_event,
#                     get_today_pracktik,prepare_message_pracktik,
#                     langList, langListKeybord, typeFiles)
# # from createKeyboard import *
# from payments import *
from dotenv import load_dotenv
import os
# from chat import GPT
# import postgreWork 
# import chromaDBwork
# from loguru import logger
# from workRedis import *
# from calendarCreate import create_calendar
# from helper import create_db,convert_text_to_variables,create_db2,get_next_weekend,find_and_format_date,find_patterns_date,create_db_for_user
from datetime import datetime,timedelta

import uuid
import time


load_dotenv()
TOKEN = os.getenv('BOT_REMOVE_SPAM')
# PAYMENTS_TOKEN = os.getenv('PAYMENTS_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK')
SECRECT_KEY = os.getenv('SECRET_CHAT')

# sql = Ydb()

router = Router()

bot = Bot(token=TOKEN,)


# from loguru import logger
# logger.add("file_{time}.log",format="{time} - {level} - {message}", rotation="100 MB", retention="10 days", level="DEBUG")
# Define the secret key and other required information

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
    # logger.debug(f'{callData=}')

           
    return 0



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
    if 'http' in text or 't.me/' in text or 'bot' in text or 'BOT' in text or '@' in text:
        # Проверяем отсутствие aibetrade
        if 'aibetrade' not in text:
            return False
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
    # if msg.chat.id not in [-1002118909508,-1002242862285,-1002231035352,-1002163616957,-1002232344340,-1002415281592]:
    #     return 0
    
    thereadID=msg.message_thread_id
    # print(f"{thereadID=}")
    # print(thereadID)
    # print(f"{msg.text.find('aibetrade')=}")  
    # print(f"{msg.text.find('http')=}")
    # print(f"{msg.text.find('t.me/')=}")
    

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
