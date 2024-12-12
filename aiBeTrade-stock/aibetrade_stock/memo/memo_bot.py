from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
import openai
import requests
from typing import Tuple, Optional
from dotenv import load_dotenv
import atexit
import fcntl
import sys
import signal
import asyncio
import aiohttp

# Загружаем переменные окружения из файла .env
load_dotenv()

# Конфигурация логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class SingletonBot:
    _lock_file = '/tmp/memo_bot.lock'
    _lock_fd = None

    @classmethod
    def check_singleton(cls):
        try:
            # Пытаемся создать и заблокировать файл
            cls._lock_fd = open(cls._lock_file, 'w')
            fcntl.flock(cls._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Записываем PID в файл блокировки
            cls._lock_fd.write(str(os.getpid()))
            cls._lock_fd.flush()
            
            # Регистрируем очистку при выходе
            atexit.register(cls.cleanup)
            signal.signal(signal.SIGTERM, cls.signal_handler)
            signal.signal(signal.SIGINT, cls.signal_handler)
            
            return True
            
        except IOError:
            logger.error("Бот уже запущен! Завершаем работу...")
            return False

    @classmethod
    def cleanup(cls):
        if cls._lock_fd:
            try:
                fcntl.flock(cls._lock_fd, fcntl.LOCK_UN)
                cls._lock_fd.close()
                os.unlink(cls._lock_file)
            except:
                pass

    @classmethod
    def signal_handler(cls, signum, frame):
        logger.info("Получен сигнал завершения, очищаем ресурсы...")
        cls.cleanup()
        sys.exit(0)

###########################################
# Переменные окружения и их значения по умолчанию
###########################################

# API ключи и токены
TELEGRAM_BOT_TOKEN = '7828437733:AAGYTT94utDZa1MPGSnvlfGLsTxa0HsmEc0'  # Токен Telegram бота
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # API ключ OpenAI

# Настройки шрифтов и текста
FONT_SIZE = int(os.getenv('FONT_SIZE', '40'))  # Размер шрифта
DEFAULT_FONT_PATH = os.getenv('DEFAULT_FONT_PATH', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')  # Путь к шрифту по умолчанию

# Настройки генерации изображений
DEFAULT_IMAGE_SIZE = os.getenv('DEFAULT_IMAGE_SIZE', '1024x1024')  # Размер генерируемого изображения
DEFAULT_IMAGE_QUALITY = os.getenv('DEFAULT_IMAGE_QUALITY', 'standard')  # Качество генерации (standard/hd)
DEFAULT_IMAGE_STYLE = os.getenv('DEFAULT_IMAGE_STYLE', 'vivid')  # Стиль изображения (vivid/natural)

# Проверка обязательных переменных окружения
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ Не установлен TELEGRAM_BOT_TOKEN")
if not OPENAI_API_KEY:
    raise ValueError("❌ Не установлен OPENAI_API_KEY")

# Инициализация OpenAI
openai.api_key = OPENAI_API_KEY

###########################################
# Константы приложения
###########################################

# Доступные шрифты
FONTS = {
    'roboto': '/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf',
    'dejavu': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    'liberation': '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    'ubuntu': '/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf',
    'noto': '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
    'freefont': '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
    'arial': 'arial.ttf',
    'times': 'times.ttf',
    'helvetica': 'helvetica.ttf',
    'verdana': 'verdana.ttf'
}

# Доступные цвета с их RGB значениями
COLORS = {
    'белый': 'white',
    'черный': 'black',
    'красный': 'red',
    'синий': 'blue',
    'зеленый': 'green',
    'желтый': 'yellow',
    'оранжевый': 'orange',
    'фиолетовый': 'purple',
    'розовый': 'pink',
    'голубой': 'cyan'
}

class MemeBot:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN):
        """Инициализация бота с настройками из переменных окружения."""
        if not SingletonBot.check_singleton():
            sys.exit(1)
            
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Генерация изображения с помощью DALL-E."""
        try:
            response = await openai.Image.acreate(
                prompt=prompt,
                n=1,
                size=DEFAULT_IMAGE_SIZE,
                quality=DEFAULT_IMAGE_QUALITY,
                style=DEFAULT_IMAGE_STYLE,
                response_format="url"
            )
            
            image_url = response.data[0].url
            # Загружаем изображение
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Ошибка при загрузке изображения: {response.status}")
                        return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {str(e)}")
            return None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start."""
        welcome_message = (
            "👋 Привет! Я бот для создания мемов и генерации изображений.\n\n"
            "🎨 Что я умею:\n"
            "1. Создавать мемы из ваших картинок\n"
            "2. Генерировать новые изображения\n\n"
            "Команды:\n"
            "/help - Показать справку\n"
            "/generate - Сгенерировать изображение"
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help."""
        help_message = (
            "🤖 Инструкция по использованию:\n\n"
            "1️⃣ Для создания мема:\n"
            "   - Отправьте мне изображение\n"
            "   - Выберите шрифт и цвет текста\n"
            "   - Напишите текст\n\n"
            "2️⃣ Для генерации изображения:\n"
            "   - Используйте команду /generate с описанием\n"
            "   Пример: /generate красивый закат на море\n\n"
            "Команды:\n"
            "/start - Начать сначала\n"
            "/help - Показать эту справку\n"
            "/generate - Создать новое изображение"
        )
        await update.message.reply_text(help_message)

    async def generate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /generate."""
        if not context.args:
            await update.message.reply_text("Пожалуйста, добавьте описание изображения после команды /generate")
            return

        prompt = ' '.join(context.args)
        message = await update.message.reply_text("🎨 Генерирую изображение, пожалуйста подождите...")

        image_data = await self.generate_image(prompt)
        if image_data:
            # Отправляем изображение
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_data,
                caption="✨ Вот ваше изображение!"
            )
            await message.delete()
        else:
            await message.edit_text("😔 Извините, произошла ошибка при генерации изображения")

    def setup_handlers(self):
        """Настройка обработчиков команд."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("generate", self.generate_command))
        
        # Добавляем обработчик ошибок
        self.application.add_error_handler(self.error_handler)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок."""
        logger.error(f"Update {update} caused error {context.error}")

    async def start(self):
        """Запуск бота."""
        await self.application.initialize()
        await self.application.start()
        logger.info("Бот запущен и готов к работе!")
        
        try:
            await self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            logger.info("Останавливаем бота...")
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Бот остановлен.")

    async def stop(self):
        """Остановка бота."""
        try:
            await self.application.stop()
            await self.application.shutdown()
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {str(e)}")

async def main():
    bot = None
    try:
        bot = MemeBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал завершения работы")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")
    finally:
        if bot:
            await bot.stop()
        SingletonBot.cleanup()

def run_bot():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
    finally:
        SingletonBot.cleanup()

if __name__ == '__main__':
    run_bot()