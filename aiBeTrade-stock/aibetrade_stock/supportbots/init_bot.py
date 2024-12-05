import os
import logging
import sys
from threading import Thread
from nfterrium_support import run_support_bot as run_nfterrium_bot
import bits_support  # Импортируем весь модуль
from pymongo import MongoClient


MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(MONGO_URI)
db = client.nntcapital
bits_settings = db["bits_settings"]
nfterrium_settings = db["nfterrium_settings"]


# Получение разрешенных пользователей
def get_ket_bot(option):
    if option == 'bits':
        bits_settings = db["bits_settings"]
    elif option == 'nfterrium':
        bits_settings = db["nfterrium_settings"]
    try:
        bot_key = bits_settings.find_one({})
        if not bot_key:
            return None
        return bot_key.get('bot_key')
    except Exception as e:
        print(f"Ошибка при получении списка разрешенных пользователей: {str(e)}")
        return None


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BitsBot')

def run_nfterrium():
    """
    Запуск бота NFTerrium
    """
    try:
        token = get_ket_bot('nfterrium')
        if not token:
            logger.error("Не удалось получить токен для NFTerrium бота")
            return
        logger.info("Запуск NFTerrium бота...")
        run_nfterrium_bot(token)
    except Exception as e:
        logger.error(f"Ошибка при запуске NFTerrium бота: {e}", exc_info=True)

def run_bits():
    """
    Запуск бота Bits
    """
    try:
        token = get_ket_bot('bits')
        if not token:
            logger.error("Не удалось получить токен для Bits бота")
            return
        logger.info("Запуск Bits бота...")
        bits_support.main()  # Вызываем main() напрямую из модуля
    except Exception as e:
        logger.error(f"Ошибка при запуске Bits бота: {e}", exc_info=True)

def main():
    """
    Основная функция запуска ботов
    """
    try:
        # Создаем потоки для каждого бота
        nfterrium_thread = Thread(target=run_nfterrium, name='NFTerriumBot')
        bits_thread = Thread(target=run_bits, name='BitsBot')
        
        # Запускаем потоки
        nfterrium_thread.start()
        logger.info("NFTerrium бот запущен в отдельном потоке")
        
        bits_thread.start()
        logger.info("Bits бот запущен в отдельном потоке")
        
        # Ожидаем завершения потоков
        nfterrium_thread.join()
        bits_thread.join()
        
    except Exception as e:
        logger.error(f"Ошибка при запуске ботов: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Запуск системы ботов...")
    main() 