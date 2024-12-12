import os
import urllib.request
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем директорию для шрифтов
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
os.makedirs(FONTS_DIR, exist_ok=True)

# URL для скачивания DejaVu Sans (как запасной вариант)
DEJAVU_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
DEJAVU_BOLD_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Bold.ttf"
DEJAVU_OBLIQUE_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-Oblique.ttf"
DEJAVU_BOLDOBLIQUE_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans-BoldOblique.ttf"

def download_font(url, filename):
    """Скачивает шрифт по URL и сохраняет в папку fonts."""
    try:
        filepath = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(filepath):
            logger.info(f"Скачиваем {filename}...")
            urllib.request.urlretrieve(url, filepath)
            logger.info(f"Шрифт {filename} успешно скачан")
        else:
            logger.info(f"Шрифт {filename} уже существует")
    except Exception as e:
        logger.error(f"Ошибка при скачивании {filename}: {str(e)}")

def main():
    """Скачивает все необходимые шрифты."""
    # Скачиваем DejaVu Sans как запасной вариант
    download_font(DEJAVU_URL, 'DejaVuSans.ttf')
    download_font(DEJAVU_BOLD_URL, 'DejaVuSans-Bold.ttf')
    download_font(DEJAVU_OBLIQUE_URL, 'DejaVuSans-Oblique.ttf')
    download_font(DEJAVU_BOLDOBLIQUE_URL, 'DejaVuSans-BoldOblique.ttf')

if __name__ == '__main__':
    main()
