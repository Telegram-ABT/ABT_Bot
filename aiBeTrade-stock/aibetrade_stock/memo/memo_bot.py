from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont
import io
import os
import logging
from typing import Tuple, Optional
import platform

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
FONT_SIZE = 40

# Определяем системный шрифт в зависимости от операционной системы
if platform.system() == 'Darwin':  # macOS
    DEFAULT_FONT = '/System/Library/Fonts/Supplemental/Arial.ttf'
elif platform.system() == 'Linux':
    DEFAULT_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
else:  # Windows
    DEFAULT_FONT = 'arial.ttf'

DEFAULT_COLOR = 'white'
AVAILABLE_COLORS = ['white', 'black', 'red', 'blue', 'green', 'yellow']
TEXT_POSITIONS = ['top', 'bottom', 'center']

class MemeBot:
    def __init__(self, token: str):
        self.updater = Updater(token)
        self.dp = self.updater.dispatcher
        self.user_data = {}
        self.setup_handlers()

    def setup_handlers(self):
        # Command handlers
        self.dp.add_handler(CommandHandler("start", self.start_command))
        self.dp.add_handler(CommandHandler("help", self.help_command))
        
        # Message handlers
        self.dp.add_handler(MessageHandler(Filters.photo, self.handle_photo))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_text))
        
        # Callback handlers
        self.dp.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Error handler
        self.dp.add_error_handler(self.error_handler)

    def start_command(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /start is issued."""
        welcome_message = (
            "👋 Привет! Я бот для создания мемов!\n\n"
            "🖼 Отправь мне изображение, и я помогу тебе создать мем.\n"
            "Ты можешь:\n"
            "- Добавлять текст сверху или снизу\n"
            "- Выбирать цвет текста\n"
            "- Менять позицию текста\n\n"
            "Используй /help для получения подробной информации."
        )
        update.message.reply_text(welcome_message)

    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Send a message when the command /help is issued."""
        help_message = (
            "📝 Как использовать бота:\n\n"
            "1. Отправь изображение\n"
            "2. Напиши текст, который хочешь добавить\n"
            "3. Выбери позицию текста и его цвет\n\n"
            "Доступные команды:\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение"
        )
        update.message.reply_text(help_message)

    def handle_photo(self, update: Update, context: CallbackContext) -> None:
        """Handle incoming photos."""
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            file = context.bot.get_file(photo.file_id)
            
            # Store photo info in user data
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
        """Handle incoming text messages."""
        user_id = update.effective_user.id
        
        if user_id not in self.user_data or self.user_data[user_id].get('stage') != 'waiting_text':
            update.message.reply_text("Сначала отправьте изображение!")
            return
        
        self.user_data[user_id]['text'] = update.message.text
        self.show_position_options(update, context)

    def show_position_options(self, update: Update, context: CallbackContext) -> None:
        """Show text position options."""
        keyboard = [
            [InlineKeyboardButton("Сверху", callback_data='pos_top'),
             InlineKeyboardButton("По центру", callback_data='pos_center'),
             InlineKeyboardButton("Снизу", callback_data='pos_bottom')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text('Выберите позицию текста:', reply_markup=reply_markup)

    def button_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks."""
        query = update.callback_query
        user_id = update.effective_user.id
        
        if user_id not in self.user_data:
            query.answer("Сессия истекла. Начните заново.")
            return
        
        data = query.data
        if data.startswith('pos_'):
            position = data.split('_')[1]
            self.user_data[user_id]['position'] = position
            self.create_meme(update, context)
        
        query.answer()

    def create_meme(self, update: Update, context: CallbackContext) -> None:
        """Create and send the meme."""
        try:
            user_id = update.effective_user.id
            user_data = self.user_data[user_id]
            
            # Download image
            image_stream = io.BytesIO()
            user_data['photo'].download(out=image_stream)
            image_stream.seek(0)
            image = Image.open(image_stream)
            
            # Prepare drawing
            draw = ImageDraw.Draw(image)
            try:
                font = ImageFont.truetype(DEFAULT_FONT, size=FONT_SIZE)
            except OSError:
                # Fallback to default font if system font is not available
                font = ImageFont.load_default()
            
            # Get text dimensions
            text = user_data['text']
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Calculate position
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
            
            # Draw text with outline for better visibility
            outline_color = 'black'
            for adj in range(-2, 3):
                for adj2 in range(-2, 3):
                    draw.text((x+adj, y+adj2), text, font=font, fill=outline_color)
            draw.text((x, y), text, font=font, fill=DEFAULT_COLOR)
            
            # Save and send image
            output_stream = io.BytesIO()
            image.save(output_stream, format='JPEG')
            output_stream.seek(0)
            
            context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=output_stream,
                caption="Вот ваш мем! Отправьте новое изображение, чтобы создать другой мем."
            )
            
            # Clear user data
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
        """Log Errors caused by Updates."""
        logger.error(f'Update "{update}" caused error "{context.error}"')
        if update:
            update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте еще раз.")

    def run(self):
        """Start the bot."""
        self.updater.start_polling()
        self.updater.idle()

def main():
    # Get bot token from environment variable
    token = '7828437733:AAGYTT94utDZa1MPGSnvlfGLsTxa0HsmEc0'
    if not token:
        raise ValueError("Please set the TELEGRAM_BOT_TOKEN environment variable")
    
    bot = MemeBot(token)
    bot.run()

if __name__ == '__main__':
    main()