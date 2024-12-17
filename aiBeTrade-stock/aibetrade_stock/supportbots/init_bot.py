import os
import logging
import sys
import psutil
import time
from threading import Thread
from datetime import datetime
from pymongo import MongoClient
import resource
from nfterrium_support import run_support_bot as run_nfterrium_bot
import bits_support

# Настройка логирования с метриками
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(metrics)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('InitBot')

# Добавляем фильтр для метрик
class MetricsFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'metrics'):
            record.metrics = ''
        return True

logger.addFilter(MetricsFilter())

# Константы для мониторинга
MEMORY_THRESHOLD = 85  # процент использования памяти
CPU_THRESHOLD = 80  # процент использования CPU
RESTART_DELAY = 60  # секунды между перезапусками
MAX_RESTARTS = 3  # максимальное количество перезапусков

# MongoDB с пулом соединений
MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(
    MONGO_URI,
    maxPoolSize=50,
    waitQueueTimeoutMS=2500,
    connectTimeoutMS=2000,
    serverSelectionTimeoutMS=3000
)
db = client.nntcapital
bits_settings = db["bits_settings"]
nfterrium_settings = db["nfterrium_settings"]

def monitor_resources():
    """
    Мониторинг системных ресурсов
    """
    while True:
        try:
            # Получаем использование ресурсов
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=1)
            memory_percent = process.memory_percent()
            
            # Получаем информацию о файловых дескрипторах
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
            
            metrics = (
                f"CPU={cpu_percent:.1f}% "
                f"MEM={memory_percent:.1f}% "
                f"FDS={num_fds}/{soft}"
            )
            
            logger.info("Мониторинг ресурсов", extra={"metrics": metrics})
            
            # Проверяем пороговые значения
            if cpu_percent > CPU_THRESHOLD or memory_percent > MEMORY_THRESHOLD:
                logger.warning(
                    f"Превышение порогов использования ресурсов",
                    extra={"metrics": metrics}
                )
        
        except Exception as e:
            logger.error(f"Ошибка в мониторинге ресурсов: {e}", exc_info=True)
        
        time.sleep(60)  # Проверяем каждую минуту

def get_ket_bot(option):
    """
    Получение ключа бота с обработкой ошибок
    """
    try:
        collection = bits_settings if option == 'bits' else nfterrium_settings
        bot_key = collection.find_one({})
        if not bot_key:
            logger.error(f"Не найден ключ для бота {option}")
            return None
        return bot_key.get('bot_key')
    except Exception as e:
        logger.error(f"Ошибка при получении ключа бота {option}: {e}", exc_info=True)
        return None

def run_bot_with_monitoring(bot_func, bot_name, token):
    """
    Запуск бота с мониторингом и автоматическим перезапуском
    """
    restart_count = 0
    while restart_count < MAX_RESTARTS:
        try:
            logger.info(f"Запуск {bot_name}...")
            start_time = time.time()
            
            if bot_name == 'NFTerrium':
                bot_func(token)
            else:
                bot_func()
                
            # Если бот завершился без ошибок, сбрасываем счетчик
            restart_count = 0
            
        except Exception as e:
            restart_count += 1
            runtime = time.time() - start_time
            
            logger.error(
                f"Ошибка в {bot_name}: {e}",
                extra={"metrics": f"runtime={runtime:.1f}s restart={restart_count}"},
                exc_info=True
            )
            
            if restart_count < MAX_RESTARTS:
                logger.info(f"Перезапуск {bot_name} через {RESTART_DELAY} секунд...")
                time.sleep(RESTART_DELAY)
            else:
                logger.critical(
                    f"{bot_name} превысил лимит перезапусков",
                    extra={"metrics": f"restarts={restart_count}"}
                )
                break

def run_nfterrium():
    """
    Запуск NFTerrium бота
    """
    token = get_ket_bot('nfterrium')
    if not token:
        logger.error("Не удалось получить токен для NFTerrium бота")
        return
    run_bot_with_monitoring(run_nfterrium_bot, 'NFTerrium', token)

def run_bits():
    """
    Запуск Bits бота
    """
    token = get_ket_bot('bits')
    if not token:
        logger.error("Не удалось получить токен для Bits бота")
        return
    run_bot_with_monitoring(bits_support.main, 'Bits', token)

def main():
    """
    Основная функция запуска ботов с мониторингом
    """
    try:
        # Запускаем мониторинг ресурсов
        monitor_thread = Thread(target=monitor_resources, daemon=True)
        monitor_thread.start()
        
        # Запускаем ботов в отдельных потоках
        nfterrium_thread = Thread(target=run_nfterrium, name='NFTerriumBot')
        bits_thread = Thread(target=run_bits, name='BitsBot')
        
        nfterrium_thread.start()
        logger.info("NFTerrium бот запущен в отдельном потоке")
        
        bits_thread.start()
        logger.info("Bits бот запущен в отдельном потоке")
        
        # Ожидаем завершения потоков
        nfterrium_thread.join()
        bits_thread.join()
        
    except Exception as e:
        logger.critical(f"Критическая ошибка в main: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    logger.info("Запуск системы ботов...")
    main()