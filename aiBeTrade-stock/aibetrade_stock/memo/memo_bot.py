from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
from openai import OpenAI
import requests
from typing import Tuple, Optional, List
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

# Пути к шрифтам
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
os.makedirs(FONTS_DIR, exist_ok=True)

# Доступные шрифты и их варианты
FONTS = {
    'Arial': {
        'regular': '/System/Library/Fonts/Supplemental/Arial.ttf',
        'bold': '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
        'italic': '/System/Library/Fonts/Supplemental/Arial Italic.ttf',
        'bold_italic': '/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf'
    },
    'Times New Roman': {
        'regular': '/System/Library/Fonts/Supplemental/Times New Roman.ttf',
        'bold': '/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf',
        'italic': '/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf',
        'bold_italic': '/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf'
    },
    'Verdana': {
        'regular': '/System/Library/Fonts/Supplemental/Verdana.ttf',
        'bold': '/System/Library/Fonts/Supplemental/Verdana Bold.ttf',
        'italic': '/System/Library/Fonts/Supplemental/Verdana Italic.ttf',
        'bold_italic': '/System/Library/Fonts/Supplemental/Verdana Bold Italic.ttf'
    },
    'Georgia': {
        'regular': '/System/Library/Fonts/Supplemental/Georgia.ttf',
        'bold': '/System/Library/Fonts/Supplemental/Georgia Bold.ttf',
        'italic': '/System/Library/Fonts/Supplemental/Georgia Italic.ttf',
        'bold_italic': '/System/Library/Fonts/Supplemental/Georgia Bold Italic.ttf'
    },
    'Comic Sans MS': {
        'regular': '/System/Library/Fonts/Supplemental/Comic Sans MS.ttf',
        'bold': '/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf',
        'italic': '/System/Library/Fonts/Supplemental/Comic Sans MS.ttf',  # Comic Sans не имеет italic
        'bold_italic': '/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf'  # и bold italic версий
    }
}

# Размеры текста
FONT_SIZES = {
    '🔍 Очень маленький': 20,
    '📝 Маленький': 30,
    '📄 Средний-': 40,
    '📑 Средний': 50,
    '📰 Средний+': 60,
    '📋 Большой-': 70,
    '📊 Большой': 80,
    '📈 Большой+': 90,
    '📉 Огромный': 100,
    '📗 Гигантский': 120
}

# Стили текста
FONT_STYLES = {
    '📝 Обычный': 'regular',
    '🖊 Жирный': 'bold',
    '✒️ Наклонный': 'italic',
    '✏️ Жирный наклонный': 'bold_italic'
}

# Цвета с эмодзи
COLORS = {
    '⚪️ Белый': 'white',
    '🟡 Жёлтый': 'yellow',
    '🔴 Красный': 'red',
    '🔵 Синий': 'blue',
    '🟢 Зелёный': 'green',
    '🟣 Фиолетовый': 'purple',
    '🟤 Коричневый': 'brown',
    '⚫️ Чёрный': 'black',
    '🟠 Оранжевый': 'orange',
    '🩷 Розовый': 'pink'
}

# Позиции текста
POSITIONS = {
    '⬆️ Сверху': 'top',
    '⬇️ Снизу': 'bottom',
    '↕️ Сверху и снизу': 'both',
    '⭐️ По центру': 'center'
}

class MemeBot:
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN):
        """Инициализация бота с настройками из переменных окружения."""
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
        # Доступные шрифты и их варианты
        self.fonts = FONTS
        
        # Размеры текста
        self.font_sizes = FONT_SIZES
        
        # Стили текста
        self.font_styles = FONT_STYLES
        
        # Цвета с эмодзи
        self.colors = COLORS
        
        # Позиции текста
        self.positions = POSITIONS

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

            # Сохраняем текст
            context.user_data['meme_text'] = update.message.text
            
            # Показываем выбор размера текста
            keyboard = []
            row = []
            for name, size in self.font_sizes.items():
                row.append(InlineKeyboardButton(name, callback_data=f'size_{size}'))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel')])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📏 Выберите размер текста:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Ошибка при обработке текста: {str(e)}")
            await update.message.reply_text("😔 Извините, произошла ошибка при обработке текста")

    async def callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик callback-запросов."""
        query = update.callback_query
        await query.answer()

        try:
            if query.data == 'cancel':
                # Очищаем данные
                context.user_data.clear()
                await query.message.edit_text("❌ Создание мема отменено")
                return

            if query.data.startswith('size_'):
                # Сохраняем выбранный размер
                size = int(query.data.replace('size_', ''))
                context.user_data['font_size'] = size
                
                # Показываем выбор стиля
                keyboard = []
                for name, style in self.font_styles.items():
                    keyboard.append([InlineKeyboardButton(name, callback_data=f'style_{style}')])
                keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(
                    "✒️ Выберите стиль текста:",
                    reply_markup=reply_markup
                )
                return

            if query.data.startswith('style_'):
                # Сохраняем выбранный стиль
                style = query.data.replace('style_', '')
                context.user_data['font_style'] = style
                
                # Показываем выбор шрифта
                keyboard = []
                row = []
                for name in self.fonts.keys():
                    row.append(InlineKeyboardButton(name, callback_data=f'font_{name}'))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(
                    "🎨 Выберите шрифт:",
                    reply_markup=reply_markup
                )
                return

            if query.data.startswith('font_'):
                # Сохраняем выбранный шрифт
                font_name = query.data.replace('font_', '')
                context.user_data['font_name'] = font_name
                
                # Показываем выбор цвета
                keyboard = []
                row = []
                for name in self.colors.keys():
                    row.append(InlineKeyboardButton(name, callback_data=f'color_{name}'))
                    if len(row) == 2:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(
                    "🎨 Выберите цвет текста:",
                    reply_markup=reply_markup
                )
                return

            if query.data.startswith('color_'):
                # Сохраняем выбранный цвет
                color_name = query.data.replace('color_', '')
                context.user_data['color'] = color_name
                
                # Показываем выбор позиции
                keyboard = []
                for name in self.positions.keys():
                    keyboard.append([InlineKeyboardButton(name, callback_data=f'pos_{name}')])
                keyboard.append([InlineKeyboardButton("Отмена", callback_data='cancel')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.edit_text(
                    "📍 Выберите расположение текста:",
                    reply_markup=reply_markup
                )
                return

            if query.data.startswith('pos_'):
                # Получаем все необходимые данные
                position = self.positions[query.data.replace('pos_', '')]
                text = context.user_data.get('meme_text')
                photo_id = context.user_data.get('current_photo')
                font_name = context.user_data.get('font_name')
                font_style = context.user_data.get('font_style')
                font_size = context.user_data.get('font_size')
                color_name = context.user_data.get('color')
                
                if not all([text, photo_id, font_name, font_style, font_size, color_name]):
                    await query.message.edit_text("😔 Что-то пошло не так, попробуйте сначала")
                    return

                # Загружаем фото
                photo_file = await context.bot.get_file(photo_id)
                photo_bytes = await photo_file.download_as_bytearray()
                
                # Создаем мем
                meme_bytes = await self.create_meme(
                    photo_bytes, 
                    text,
                    os.path.join(FONTS_DIR, self.fonts[font_name][font_style]),
                    self.colors[color_name],
                    position,
                    font_size
                )
                
                if meme_bytes:
                    # Отправляем готовый мем
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=meme_bytes,
                        caption=f"✨ Ваш мем готов!\nШрифт: {font_name}\nСтиль: {font_style}\nРазмер: {font_size}\nЦвет: {color_name}"
                    )
                    await query.message.delete()
                else:
                    await query.message.edit_text("😔 Извините, произошла ошибка при создании мема")
                
                # Очищаем данные
                context.user_data.clear()
                
        except Exception as e:
            logger.error(f"Ошибка в callback_query: {str(e)}")
            await query.message.edit_text("😔 Произошла ошибка, попробуйте сначала")
            context.user_data.clear()

    def _draw_text_with_outline(self, draw, position, text, font, text_color):
        """Рисует текст с обводкой."""
        x, y = position
        # Рисуем обводку
        outline_color = 'black'
        for adj in range(-2, 3):
            for adj2 in range(-2, 3):
                draw.text((x+adj, y+adj2), text, font=font, fill=outline_color)
        # Рисуем основной текст
        draw.text((x, y), text, font=font, fill=text_color)

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Разбивает текст на строки, чтобы он поместился в указанную ширину."""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Добавляем слово к текущей строке
            test_line = ' '.join(current_line + [word])
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
            
            if width <= max_width:
                current_line.append(word)
            else:
                # Если текущая строка не пустая, добавляем её к результату
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        # Добавляем последнюю строку
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    async def create_meme(self, image_bytes: bytes, text: str, font_path: str, text_color: str, position: str, font_size: int) -> Optional[bytes]:
        """Создание мема из изображения и текста."""
        try:
            # Открываем изображение
            image = Image.open(io.BytesIO(image_bytes))
            
            # Создаем новое RGBA изображение
            new_image = Image.new('RGBA', image.size, (0, 0, 0, 0))
            new_image.paste(image)
            
            # Создаем объект для рисования
            draw = ImageDraw.Draw(new_image)
            
            # Загружаем шрифт
            try:
                font = ImageFont.truetype(font_path, font_size)
            except Exception as e:
                logger.error(f"Ошибка загрузки шрифта {font_path}: {str(e)}")
                # Пробуем загрузить обычный Arial как запасной вариант
                try:
                    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', font_size)
                except Exception as e:
                    logger.error(f"Ошибка загрузки запасного шрифта Arial: {str(e)}")
                    # Если и это не получилось, используем дефолтный шрифт
                    font = ImageFont.load_default()
                    logger.warning("Используется системный шрифт по умолчанию")
            
            # Получаем размеры изображения
            width, height = new_image.size
            
            # Разбиваем текст на строки
            lines = self._wrap_text(text, font, width - 20)
            
            # Вычисляем высоту одной строки
            line_spacing = 5  # дополнительный отступ между строками
            line_height = font.size + line_spacing
            text_height = len(lines) * line_height
            
            # Определяем позицию текста
            if position == 'top':
                y = 10
            elif position == 'bottom':
                y = height - text_height - 10
            elif position == 'center':
                y = (height - text_height) // 2
            else:  # both
                # Разделяем текст пополам
                mid = len(lines) // 2
                top_lines = lines[:mid]
                bottom_lines = lines[mid:]
                
                # Рисуем верхний текст
                y = 10
                for line in top_lines:
                    bbox = font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                    x = (width - line_width) // 2
                    self._draw_text_with_outline(draw, (x, y), line, font, text_color)
                    y += line_height
                
                # Рисуем нижний текст
                y = height - len(bottom_lines) * line_height - 10
                for line in bottom_lines:
                    bbox = font.getbbox(line)
                    line_width = bbox[2] - bbox[0]
                    x = (width - line_width) // 2
                    self._draw_text_with_outline(draw, (x, y), line, font, text_color)
                    y += line_height
                
                # Конвертируем в RGB и сохраняем
                rgb_image = Image.new('RGB', new_image.size, (255, 255, 255))
                rgb_image.paste(new_image, mask=new_image.split()[3])
                
                # Сохраняем результат
                output = io.BytesIO()
                rgb_image.save(output, format='JPEG', quality=95)
                output.seek(0)
                return output.getvalue()
            
            # Для остальных позиций рисуем текст
            for line in lines:
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                self._draw_text_with_outline(draw, (x, y), line, font, text_color)
                y += line_height
            
            # Конвертируем в RGB и сохраняем
            rgb_image = Image.new('RGB', new_image.size, (255, 255, 255))
            rgb_image.paste(new_image, mask=new_image.split()[3])
            
            # Сохраняем результат
            output = io.BytesIO()
            rgb_image.save(output, format='JPEG', quality=95)
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Ошибка при создании мема: {str(e)}")
            return None

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