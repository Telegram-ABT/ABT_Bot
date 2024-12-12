import os
import requests
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL-адреса открытых шрифтов
FONT_URLS = {
    # Open Sans
    'OpenSans-Regular.ttf': 'https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-Regular.ttf',
    'OpenSans-Bold.ttf': 'https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-Bold.ttf',
    'OpenSans-Italic.ttf': 'https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-Italic.ttf',
    'OpenSans-BoldItalic.ttf': 'https://raw.githubusercontent.com/googlefonts/opensans/main/fonts/ttf/OpenSans-BoldItalic.ttf',
    
    # Roboto
    'Roboto-Regular.ttf': 'https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf',
    'Roboto-Bold.ttf': 'https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf',
    'Roboto-Italic.ttf': 'https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Italic.ttf',
    'Roboto-BoldItalic.ttf': 'https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-BoldItalic.ttf',
    
    # PT Sans
    'PTSans-Regular.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ptsans/PTSans-Regular.ttf',
    'PTSans-Bold.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ptsans/PTSans-Bold.ttf',
    'PTSans-Italic.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ptsans/PTSans-Italic.ttf',
    'PTSans-BoldItalic.ttf': 'https://raw.githubusercontent.com/google/fonts/main/ofl/ptsans/PTSans-BoldItalic.ttf'
}

def download_fonts():
    # Создаем директорию fonts если она не существует
    fonts_dir = Path(__file__).parent / 'fonts'
    fonts_dir.mkdir(exist_ok=True)
    
    for font_name, url in FONT_URLS.items():
        font_path = fonts_dir / font_name
        
        # Пропускаем если файл уже существует
        if font_path.exists():
            logger.info(f"Шрифт {font_name} уже существует")
            continue
            
        try:
            logger.info(f"Скачиваем шрифт {font_name}...")
            response = requests.get(url)
            response.raise_for_status()
            
            with open(font_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Шрифт {font_name} успешно скачан")
            
        except Exception as e:
            logger.error(f"Ошибка при скачивании шрифта {font_name}: {str(e)}")

if __name__ == '__main__':
    download_fonts()
