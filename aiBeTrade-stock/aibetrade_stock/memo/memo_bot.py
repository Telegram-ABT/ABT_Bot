from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
from openai import OpenAI
import requests
from typing import Tuple, Optional
from dotenv import load_dotenv
import asyncio
import aiohttp

# Загружаем переменные окружения из файла .env
load_dotenv()

# Конфигурация логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# API ключи и токены
TELEGRAM_BOT_TOKEN = '7828437733:AAGYTT94utDZa1MPGSnvlfGLsTxa0HsmEc0'  # Токен Telegram бота
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')  # API ключ OpenAI

# Настройки шрифтов и текста
FONT_SIZE = int(os.getenv('FONT_SIZE', '40'))  # Размер шрифта
DEFAULT_FONT_PATH = os.getenv('DEFAULT_FONT_PATH', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')  # Путь к шрифту по умолчанию

# Константы для генерации изображений
DEFAULT_IMAGE_SIZE = "1024x1024"
DEFAULT_IMAGE_QUALITY = "standard"
DEFAULT_IMAGE_STYLE = "vivid"

# Инициализация клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Проверка обязательных переменных окружения
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ Не установлен TELEGRAM_BOT_TOKEN")
if not OPENAI_API_KEY:
    raise ValueError("❌ Не установлен OPENAI_API_KEY")

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
        self.application = Application.builder().token(token).build()
        self.setup_handlers()

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Генерация изображения с помощью DALL-E."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.images.generate(
                    prompt=prompt,
                    n=1,
                    size=DEFAULT_IMAGE_SIZE,
                    quality=DEFAULT_IMAGE_QUALITY,
                    style=DEFAULT_IMAGE_STYLE
                )
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

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик входящих фотографий."""
        try:
            # Получаем файл с наилучшим качеством
            photo = update.message.photo[-1]
            
            # Сохраняем информацию о фото в контексте пользователя
            context.user_data['current_photo'] = photo.file_id
            
            # Запрашиваем текст для мема
            keyboard = [
                [InlineKeyboardButton("Отмена", callback_data='cancel')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📝 Отправьте текст, который нужно добавить на изображение\n"
                "Или нажмите 'Отмена' для отмены",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка в handle_photo: {str(e)}")
            await update.message.reply_text("😔 Произошла ошибка при обработке фото")

    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текста для создания мема."""
        try:
            if 'current_photo' not in context.user_data:
                await update.message.reply_text("Сначала отправьте изображение!")
                return

            # Получаем фото и текст
            photo_file_id = context.user_data['current_photo']
            text = update.message.text

            # Загружаем фото
            photo_file = await context.bot.get_file(photo_file_id)
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Создаем мем
            meme_bytes = await self.create_meme(photo_bytes, text)
            
            if meme_bytes:
                # Отправляем готовый мем
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=meme_bytes,
                    caption="✨ Ваш мем готов!"
                )
            else:
                await update.message.reply_text("😔 Извините, произошла ошибка при создании мема")
            
            # Очищаем данные
            del context.user_data['current_photo']
            
        except Exception as e:
            logger.error(f"Ошибка при создании мема: {str(e)}")
            await update.message.reply_text("😔 Извините, произошла ошибка при создании мема")

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик callback-запросов."""
        query = update.callback_query
        await query.answer()

        if query.data == 'cancel':
            if 'current_photo' in context.user_data:
                del context.user_data['current_photo']
            await query.message.edit_text("❌ Создание мема отменено")

    async def create_meme(self, image_bytes: bytes, text: str) -> Optional[bytes]:
        """Создание мема из изображения и текста."""
        try:
            # Открываем изображение
            image = Image.open(io.BytesIO(image_bytes))
            
            # Создаем объект для рисования
            draw = ImageDraw.Draw(image)
            
            # Загружаем шрифт
            try:
                font = ImageFont.truetype(DEFAULT_FONT_PATH, FONT_SIZE)
            except:
                # Если не удалось загрузить шрифт, используем дефолтный
                font = ImageFont.load_default()
            
            # Получаем размеры изображения
            width, height = image.size
            
            # Разбиваем текст на строки
            lines = self._wrap_text(text, font, width - 20)
            
            # Вычисляем общую высоту текста
            line_height = font.getsize('hg')[1] + 5
            text_height = len(lines) * line_height
            
            # Рисуем каждую строку текста
            y = height - text_height - 10
            for line in lines:
                # Вычисляем ширину текста
                line_width = font.getsize(line)[0]
                
                # Центрируем текст
                x = (width - line_width) // 2
                
                # Рисуем обводку
                for offset in range(-2, 3):
                    for offset2 in range(-2, 3):
                        draw.text((x + offset, y + offset2), line, font=font, fill='black')
                
                # Рисуем текст
                draw.text((x, y), line, font=font, fill='white')
                
                y += line_height
            
            # Сохраняем результат
            output = io.BytesIO()
            image.save(output, format='JPEG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка при создании мема: {str(e)}")
            return None

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
        """Разбивает текст на строки, чтобы он поместился по ширине."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Добавляем слово к текущей строке
            current_line.append(word)
            
            # Проверяем ширину
            line = ' '.join(current_line)
            width = font.getsize(line)[0]
            
            # Если строка слишком широкая, начинаем новую строку
            if width > max_width:
                # Убираем последнее слово
                current_line.pop()
                
                # Добавляем строку к результату
                if current_line:
                    lines.append(' '.join(current_line))
                
                # Начинаем новую строку с убранным словом
                current_line = [word]
        
        # Добавляем последнюю строку
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def setup_handlers(self):
        """Настройка обработчиков команд."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("generate", self.generate_command))
        
        # Добавляем обработчики для создания мемов
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(CallbackQueryHandler(self.callback_query))
        
        # Добавляем обработчик ошибок
        self.application.add_error_handler(self.error_handler)

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок."""
        logger.error(f"Update {update} caused error {context.error}")

if __name__ == '__main__':
    try:
        # Создаем бота
        bot = MemeBot()
        
        # Запускаем бота
        bot.application.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")