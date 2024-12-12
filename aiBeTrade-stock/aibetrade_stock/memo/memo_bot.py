from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
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
            
        self.updater = Updater(token)
        self.dp = self.updater.dispatcher
        self.user_data = {}
        self.setup_handlers()

    async def generate_image(self, prompt: str) -> Optional[bytes]:
        """Генерация изображения с помощью DALL-E."""
        try:
            response = await openai.Image.create(
                prompt=prompt,
                n=1,
                size=DEFAULT_IMAGE_SIZE,
                quality=DEFAULT_IMAGE_QUALITY,
                style=DEFAULT_IMAGE_STYLE,
                response_format="url"
            )
            
            image_url = response.data[0].url
            # Загружаем изображение
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                return image_response.content
            else:
                logger.error(f"Ошибка при загрузке изображения: {image_response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {str(e)}")
            return None

    async def generate_command(self, update: Update, context: CallbackContext):
        """Обработчик команды /generate."""
        if not context.args:
            await update.message.reply_text("Пожалуйста, добавьте описание изображения после команды /generate")
            return

        prompt = ' '.join(context.args)
        await update.message.reply_text("🎨 Генерирую изображение, пожалуйста подождите...")

        image_data = await self.generate_image(prompt)
        if image_data:
            # Отправляем изображение
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=image_data,
                caption="✨ Вот ваше изображение!"
            )
        else:
            await update.message.reply_text("😔 Извините, произошла ошибка при генерации изображения")

    def setup_handlers(self):
        self.dp.add_handler(CommandHandler("start", self.start_command))
        self.dp.add_handler(CommandHandler("help", self.help_command))
        self.dp.add_handler(CommandHandler("generate", self.generate_command))
        self.dp.add_handler(MessageHandler(Filters.photo, self.handle_photo))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_text))
        self.dp.add_handler(CallbackQueryHandler(self.button_callback))
        self.dp.add_error_handler(self.error_handler)

    def start_command(self, update: Update, context: CallbackContext) -> None:
        welcome_message = (
            "👋 Привет! Я бот для создания мемов!\n\n"
            "🖼 У меня есть несколько возможностей:\n"
            "1. Отправь мне изображение, и я добавлю на него текст\n"
            "2. Используй команду /generate с описанием, и я создам новое изображение\n\n"
            "Ты можешь:\n"
            "- Выбирать из 10 различных шрифтов\n"
            "- Использовать 10 разных цветов текста\n"
            "- Менять позицию текста\n\n"
            "Используй /help для получения подробной информации."
        )
        update.message.reply_text(welcome_message)

    def help_command(self, update: Update, context: CallbackContext) -> None:
        help_message = (
            "📝 Как использовать бота:\n\n"
            "1. Создание мема из существующего изображения:\n"
            "   - Отправь изображение\n"
            "   - Напиши текст\n"
            "   - Выбери шрифт, цвет и позицию\n\n"
            "2. Создание нового изображения:\n"
            "   - Используй команду /generate\n"
            "   - Напиши описание желаемого изображения\n\n"
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/generate - Создать новое изображение"
        )
        update.message.reply_text(help_message)

    def show_font_options(self, update: Update, context: CallbackContext) -> None:
        keyboard = []
        row = []
        for i, (font_name, _) in enumerate(FONTS.items()):
            if i > 0 and i % 2 == 0:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(font_name, callback_data=f'font_{font_name}'))
        if row:
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Выберите шрифт:', reply_markup=reply_markup)

    def show_color_options(self, update: Update, context: CallbackContext) -> None:
        keyboard = []
        row = []
        for i, (color_name, _) in enumerate(COLORS.items()):
            if i > 0 and i % 2 == 0:
                keyboard.append(row)
                row = []
            row.append(InlineKeyboardButton(color_name, callback_data=f'color_{color_name}'))
        if row:
            keyboard.append(row)
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Выберите цвет текста:', reply_markup=reply_markup)

    def handle_photo(self, update: Update, context: CallbackContext) -> None:
        try:
            photo = update.message.photo[-1]
            file = context.bot.get_file(photo.file_id)
            
            user_id = update.effective_user.id
            self.user_data[user_id] = {
                'photo': file,
                'stage': 'waiting_text'
            }
            
            update.message.reply_text("Отлично! Теперь отправь мне текст для мема.")
            
        except Exception as e:
            logger.error(f"Error handling photo: {str(e)}")
            update.message.reply_text("Произошла ошибка при обработке фото. Попробуйте еще раз.")

    def handle_text(self, update: Update, context: CallbackContext) -> None:
        user_id = update.effective_user.id
        
        if user_id not in self.user_data or self.user_data[user_id].get('stage') != 'waiting_text':
            update.message.reply_text("Сначала отправьте изображение!")
            return
        
        self.user_data[user_id]['text'] = update.message.text
        self.user_data[user_id]['stage'] = 'choosing_font'
        self.show_font_options(update, context)

    def button_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            query.answer("Сессия истекла. Начните заново.")
            return

        data = query.data
        if data.startswith('font_'):
            font_name = data.split('_')[1]
            self.user_data[user_id]['font'] = font_name
            self.user_data[user_id]['stage'] = 'choosing_color'
            self.show_color_options(update.effective_message, context)
        elif data.startswith('color_'):
            color_name = data.split('_')[1]
            self.user_data[user_id]['color'] = COLORS[color_name]
            self.show_position_options(update.effective_message, context)
        elif data.startswith('pos_'):
            position = data.split('_')[1]
            self.user_data[user_id]['position'] = position
            self.create_meme(update, context)
        
        query.answer()

    def show_position_options(self, update: Update, context: CallbackContext) -> None:
        keyboard = [
            [InlineKeyboardButton("Сверху", callback_data='pos_top'),
             InlineKeyboardButton("По центру", callback_data='pos_center'),
             InlineKeyboardButton("Снизу", callback_data='pos_bottom')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.reply_text('Выберите позицию текста:', reply_markup=reply_markup)

    def create_meme(self, update: Update, context: CallbackContext) -> None:
        try:
            user_id = update.effective_user.id
            user_data = self.user_data[user_id]
            
            image_stream = io.BytesIO()
            user_data['photo'].download(out=image_stream)
            image_stream.seek(0)
            image = Image.open(image_stream)
            
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype(FONTS[user_data['font']], size=FONT_SIZE)
            except OSError:
                font = ImageFont.load_default()
            
            text = user_data['text']
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            width, height = image.size
            position = user_data['position']
            if position == 'top':
                x = (width - text_width) / 2
                y = 10
            elif position == 'center':
                x = (width - text_width) / 2
                y = (height - text_height) / 2
            else:  # bottom
                x = (width - text_width) / 2
                y = height - text_height - 10
            
            outline_color = 'black'
            for adj in range(-2, 3):
                for adj2 in range(-2, 3):
                    draw.text((x+adj, y+adj2), text, font=font, fill=outline_color)
            draw.text((x, y), text, font=font, fill=user_data['color'])
            
            output_stream = io.BytesIO()
            image.save(output_stream, format='JPEG')
            output_stream.seek(0)
            
            context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=output_stream,
                caption="Вот ваш мем! Отправьте новое изображение, чтобы создать другой мем."
            )
            
            del self.user_data[user_id]
            
        except Exception as e:
            logger.error(f"Error creating meme: {str(e)}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Произошла ошибка при создании мема. Попробуйте еще раз."
            )
            if user_id in self.user_data:
                del self.user_data[user_id]

    def error_handler(self, update: Update, context: CallbackContext) -> None:
        logger.error(f'Update "{update}" caused error "{context.error}"')
        if update:
            update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте еще раз.")

    def run(self):
        self.updater.start_polling()
        self.updater.idle()

def main():
    try:
        bot = MemeBot()
        logger.info("Бот запущен. Нажмите Ctrl+C для завершения.")
        bot.run()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")
        SingletonBot.cleanup()
        sys.exit(1)

if __name__ == '__main__':
    main()