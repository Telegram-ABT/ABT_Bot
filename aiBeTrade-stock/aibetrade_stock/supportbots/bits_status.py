from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime, UTC
from pymongo import MongoClient
from bson import ObjectId
import os
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('BitsBot')

# Подключение к MongoDB
MONGO_URI = os.getenv('MONGO_URL_SERV')
client = MongoClient(MONGO_URI)
db = client.nntcapital

# Языки и их отображение
LANGUAGES = {
    'ru': '🇷🇺 Русский',
    'en': '🇬🇧 English',
    'fra': '🇫🇷 Français',
    'deu': '🇩🇪 Deutsch',
    'esp': '🇪🇸 Español',
    'zh': '🇨🇳 中文'
}

# Тексты для разных языков
TEXTS = {
    'ru': {
        'no_user_data': 'Данные пользователя не обнаружены',
        'no_connections': 'У вас нет подключенных аккаунтов бирж',
        'create_account': 'Создать аккаунт биржи',
        'back': 'Назад',
        'select_exchange': 'Выберите биржу:',
        'enter_key': 'Введите ключ API (должен быть 10 символов):',
        'invalid_key': 'Ключ введен не корректно, повторите отправку',
        'enter_secret': 'Введите секретный ключ (должен быть 15 символов):',
        'invalid_secret': 'Секретный ключ введен не корректно, повторите отправку',
        'enter_deposit': 'Введите сумму стартового депозита (минимум 1000 USDT):',
        'invalid_deposit': 'Сумма депозита введена не корректно, она должна быть более 1000 usdt',
        'confirm': 'Подтвердить',
        'edit': 'Изменить',
        'delete': 'Удалить',
        'connection_info': """
Информация о подключении:
Connection ID: {connection_id}
Биржа: {stock}
Key: {key}
Secret Key: {secret_key}
Стартовый депозит: {start_dep} USDT
Дата начала: {start_data}
Период оплаты: {pay_period} дней
Доля прибыли: {share_profit}%""",
        'confirm_delete': 'Вы уверены, что хотите удалить это подключение?',
        'confirm_delete_btn': 'Подтвердить удаление',
        'cancel': 'Отменить',
        'deleted_successfully': 'Подключение успешно удалено'
    },
    'en': {
        'no_user_data': 'User data not found',
        'no_connections': 'You have no connected exchange accounts',
        'create_account': 'Create exchange account',
        'back': 'Back',
        'select_exchange': 'Select exchange:',
        'enter_key': 'Enter API key (must be 10 characters):',
        'invalid_key': 'Invalid key, please try again',
        'enter_secret': 'Enter secret key (must be 15 characters):',
        'invalid_secret': 'Invalid secret key, please try again',
        'enter_deposit': 'Enter initial deposit amount (minimum 1000 USDT):',
        'invalid_deposit': 'Invalid deposit amount, it must be more than 1000 USDT',
        'confirm': 'Confirm',
        'edit': 'Edit',
        'delete': 'Delete',
        'connection_info': """
Connection Information:
Connection ID: {connection_id}
Exchange: {stock}
Key: {key}
Secret Key: {secret_key}
Initial Deposit: {start_dep} USDT
Start Date: {start_data}
Payment Period: {pay_period} days
Profit Share: {share_profit}%""",
        'confirm_delete': 'Are you sure you want to delete this connection?',
        'confirm_delete_btn': 'Confirm deletion',
        'cancel': 'Cancel',
        'deleted_successfully': 'Connection successfully deleted'
    },
    'fra': {
        'no_user_data': 'Données utilisateur non trouvées',
        'no_connections': "Vous n'avez pas de comptes d'échange connectés",
        'create_account': "Créer un compte d'échange",
        'back': 'Retour',
        'select_exchange': 'Sélectionnez une bourse:',
        'enter_key': "Entrez la clé API (doit être de 10 caractères):",
        'invalid_key': 'Clé invalide, veuillez réessayer',
        'enter_secret': 'Entrez la clé secrète (doit être de 15 caractères):',
        'invalid_secret': 'Clé secrète invalide, veuillez réessayer',
        'enter_deposit': 'Entrez le montant du dépôt initial (minimum 1000 USDT):',
        'invalid_deposit': 'Montant du dépôt invalide, il doit être supérieur à 1000 USDT',
        'confirm': 'Confirmer',
        'edit': 'Modifier',
        'delete': 'Supprimer',
        'connection_info': """
Informations de connexion:
ID de connexion: {connection_id}
Bourse: {stock}
Clé: {key}
Clé secrète: {secret_key}
Dépôt initial: {start_dep} USDT
Date de début: {start_data}
Période de paiement: {pay_period} jours
Part des bénéfices: {share_profit}%""",
        'confirm_delete': 'Êtes-vous sûr de vouloir supprimer cette connexion?',
        'confirm_delete_btn': 'Confirmer la suppression',
        'cancel': 'Annuler',
        'deleted_successfully': 'Connexion supprimée avec succès'
    },
    'deu': {
        'no_user_data': 'Benutzerdaten nicht gefunden',
        'no_connections': 'Sie haben keine verbundenen Börsenkonten',
        'create_account': 'Börsenkonto erstellen',
        'back': 'Zurück',
        'select_exchange': 'Wählen Sie eine Börse:',
        'enter_key': 'API-Schlüssel eingeben (muss 10 Zeichen lang sein):',
        'invalid_key': 'Ungültiger Schlüssel, bitte versuchen Sie es erneut',
        'enter_secret': 'Geheimen Schlüssel eingeben (muss 15 Zeichen lang sein):',
        'invalid_secret': 'Ungültiger geheimer Schlüssel, bitte versuchen Sie es erneut',
        'enter_deposit': 'Geben Sie den anfänglichen Einzahlungsbetrag ein (mindestens 1000 USDT):',
        'invalid_deposit': 'Ungültiger Einzahlungsbetrag, er muss mehr als 1000 USDT betragen',
        'confirm': 'Bestätigen',
        'edit': 'Bearbeiten',
        'delete': 'Löschen',
        'connection_info': """
Verbindungsinformationen:
Verbindungs-ID: {connection_id}
Börse: {stock}
Schlüssel: {key}
Geheimer Schlüssel: {secret_key}
Anfängliche Einzahlung: {start_dep} USDT
Startdatum: {start_data}
Zahlungsperiode: {pay_period} Tage
Gewinnbeteiligung: {share_profit}%""",
        'confirm_delete': 'Sind Sie sicher, dass Sie diese Verbindung löschen möchten?',
        'confirm_delete_btn': 'Löschen bestätigen',
        'cancel': 'Abbrechen',
        'deleted_successfully': 'Verbindung erfolgreich gelöscht'
    },
    'esp': {
        'no_user_data': 'Datos de usuario no encontrados',
        'no_connections': 'No tiene cuentas de intercambio conectadas',
        'create_account': 'Crear cuenta de intercambio',
        'back': 'Atrás',
        'select_exchange': 'Seleccione un intercambio:',
        'enter_key': 'Ingrese la clave API (debe tener 10 caracteres):',
        'invalid_key': 'Clave inválida, por favor intente de nuevo',
        'enter_secret': 'Ingrese la clave secreta (debe tener 15 caracteres):',
        'invalid_secret': 'Clave secreta inválida, por favor intente de nuevo',
        'enter_deposit': 'Ingrese el monto del depósito inicial (mínimo 1000 USDT):',
        'invalid_deposit': 'Monto de depósito inválido, debe ser mayor a 1000 USDT',
        'confirm': 'Confirmar',
        'edit': 'Editar',
        'delete': 'Eliminar',
        'connection_info': """
Información de conexión:
ID de conexión: {connection_id}
Intercambio: {stock}
Clave: {key}
Clave secreta: {secret_key}
Depósito inicial: {start_dep} USDT
Fecha de inicio: {start_data}
Período de pago: {pay_period} días
Participación en beneficios: {share_profit}%""",
        'confirm_delete': '¿Está seguro de que desea eliminar esta conexión?',
        'confirm_delete_btn': 'Confirmar eliminación',
        'cancel': 'Cancelar',
        'deleted_successfully': 'Conexión eliminada con éxito'
    },
    'zh': {
        'no_user_data': '未找到用户数据',
        'no_connections': '您没有连接的交易所账户',
        'create_account': '创建交易所账户',
        'back': '返回',
        'select_exchange': '选择交易所：',
        'enter_key': '输入API密钥（必须是10个字符）：',
        'invalid_key': '无效的密钥，请重试',
        'enter_secret': '输入密钥（必须是15个字符）：',
        'invalid_secret': '无效的密钥，请重试',
        'enter_deposit': '输入初始存款金额（最少1000 USDT）：',
        'invalid_deposit': '存款金额无效，必须超过1000 USDT',
        'confirm': '确认',
        'edit': '编辑',
        'delete': '删除',
        'connection_info': """
连接信息：
连接ID：{connection_id}
交易所：{stock}
密钥：{key}
密钥：{secret_key}
初始存款：{start_dep} USDT
开始日期：{start_data}
支付周期：{pay_period} 天
利润分成：{share_profit}%""",
        'confirm_delete': '您确定要删除此连接吗？',
        'confirm_delete_btn': '确认删除',
        'cancel': '取消',
        'deleted_successfully': '连接已成功删除'
    }
}

def get_user_language(user_id: int) -> str:
    """Получает язык пользователя из БД"""
    try:
        user_settings = db.bits_user_settings.find_one({'user_id': user_id})
        return user_settings['language'] if user_settings else 'en'
    except Exception as e:
        logger.error(f"Ошибка при получении языка пользователя: {e}")
        return 'en'

def create_exchange_menu(lang: str) -> InlineKeyboardMarkup:
    """Создает меню выбора биржи"""
    markup = InlineKeyboardMarkup()
    exchanges = ['Bybit', 'Binance', 'OKX', 'Bitget']
    for exchange in exchanges:
        markup.add(InlineKeyboardButton(exchange, callback_data=f'exchange_{exchange.lower()}'))
    markup.add(InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_to_main'))
    return markup

def create_connection_menu(connection, lang: str) -> InlineKeyboardMarkup:
    """Создает меню для управления подключением"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton('✅ ' + TEXTS[lang]['confirm'], callback_data=f'confirm_{connection["_id"]}'),
        InlineKeyboardButton('🔄 ' + TEXTS[lang]['edit'], callback_data=f'edit_{connection["_id"]}')
    )
    markup.row(
        InlineKeyboardButton('❌ ' + TEXTS[lang]['delete'], callback_data=f'delete_{connection["_id"]}'),
        InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_to_main')
    )
    return markup

def get_status_user(message: Message, bot: TeleBot, lang: str):
    """Получает и отображает статус пользователя"""
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    # Проверяем наличие пользователя в bits_user_settings
    user_settings = db.bits_user_settings.find_one({'user_id': user_id})
    if not user_settings:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(TEXTS[lang]['create_account'], callback_data='create_account'))
        markup.add(InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_to_main'))
        bot.reply_to(message, TEXTS[lang]['no_user_data'], reply_markup=markup)
        return
    
    # Проверяем подключения пользователя
    user_connections = list(db.bits_user_connection.find({'user_id': user_id}))
    if not user_connections:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(TEXTS[lang]['create_account'], callback_data='create_account'))
        markup.add(InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_to_main'))
        bot.reply_to(message, TEXTS[lang]['no_connections'], reply_markup=markup)
        return
    
    # Создаем меню с существующими подключениями
    markup = InlineKeyboardMarkup()
    for conn in user_connections:
        button_text = f"{conn['connection_id']} - {conn['stock']}"
        markup.add(InlineKeyboardButton(button_text, callback_data=f'connection_{conn["_id"]}'))
    markup.add(InlineKeyboardButton(TEXTS[lang]['create_account'], callback_data='create_account'))
    markup.add(InlineKeyboardButton(TEXTS[lang]['back'], callback_data='back_to_main'))
    
    bot.reply_to(message, TEXTS[lang]['select_exchange'], reply_markup=markup)

def handle_new_connection(message: Message, bot: TeleBot, state: dict):
    """Обработка создания нового подключения"""
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    if 'step' not in state:
        markup = create_exchange_menu(lang)
        bot.reply_to(message, TEXTS[lang]['select_exchange'], reply_markup=markup)
        state['step'] = 'exchange'
        return
    
    if state['step'] == 'key':
        key = message.text.strip()
        if len(key) != 10:
            bot.reply_to(message, TEXTS[lang]['invalid_key'])
            return
        state['key'] = key
        state['step'] = 'secret'
        bot.reply_to(message, TEXTS[lang]['enter_secret'])
        return
    
    if state['step'] == 'secret':
        secret = message.text.strip()
        if len(secret) != 15:
            bot.reply_to(message, TEXTS[lang]['invalid_secret'])
            return
        state['secret_key'] = secret
        state['step'] = 'deposit'
        bot.reply_to(message, TEXTS[lang]['enter_deposit'])
        return
    
    if state['step'] == 'deposit':
        try:
            deposit = float(message.text.strip())
            if deposit < 1000:
                bot.reply_to(message, TEXTS[lang]['invalid_deposit'])
                return
            
            # Вычисляем параметры
            pay_period = 30 if deposit < 10000 else 90
            if deposit < 10000:
                share_profit = 30
            elif deposit < 50000:
                share_profit = 25
            else:
                share_profit = 20
            
            # Создаем новую запись
            connection_data = {
                'user_id': user_id,
                'connection_id': f"CONN_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                'stock': state['exchange'],
                'key': state['key'],
                'secret_key': state['secret_key'],
                'start_dep': deposit,
                'start_data': datetime.now(UTC),
                'pay_period': pay_period,
                'share_profit': share_profit
            }
            
            db.bits_user_connection.insert_one(connection_data)
            
            # Отправляем информацию о созданном подключении
            bot.reply_to(
                message,
                TEXTS[lang]['connection_info'].format(**connection_data),
                reply_markup=create_connection_menu(connection_data, lang)
            )
            
            # Очищаем состояние
            state.clear()
            
        except ValueError:
            bot.reply_to(message, TEXTS[lang]['invalid_deposit'])
            return

def create_delete_confirmation_menu(connection_id: str, lang: str) -> InlineKeyboardMarkup:
    """Создает меню подтверждения удаления"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(
            '❌ ' + TEXTS[lang]['confirm_delete_btn'],
            callback_data=f'confirm_delete_{connection_id}'
        ),
        InlineKeyboardButton(
            '↩️ ' + TEXTS[lang]['cancel'],
            callback_data=f'cancel_delete_{connection_id}'
        )
    )
    return markup

def handle_delete_connection(message: Message, connection_id: str, bot: TeleBot):
    """Обработка запроса на удаление подключения"""
    try:
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        
        # Проверяем существование подключения и права пользователя
        connection = db.bits_user_connection.find_one({
            '_id': ObjectId(connection_id),
            'user_id': user_id
        })
        
        if not connection:
            return
        
        # Показываем меню подтверждения
        bot.edit_message_text(
            TEXTS[lang]['confirm_delete'],
            message.chat.id,
            message.message_id,
            reply_markup=create_delete_confirmation_menu(connection_id, lang)
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке удаления: {e}", exc_info=True)

def handle_confirm_delete(message: Message, connection_id: str, bot: TeleBot):
    """Обработка подтверждения удаления"""
    try:
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        
        # Удаляем подключение
        result = db.bits_user_connection.delete_one({
            '_id': ObjectId(connection_id),
            'user_id': user_id
        })
        
        if result.deleted_count > 0:
            # Показываем сообщение об успешном удалении
            bot.edit_message_text(
                TEXTS[lang]['deleted_successfully'],
                message.chat.id,
                message.message_id
            )
            # Возвращаем пользователя к списку подключений
            get_status_user(message, bot)
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении удаления: {e}", exc_info=True)

def handle_cancel_delete(message: Message, connection_id: str, bot: TeleBot):
    """Обработка отмены удаления"""
    try:
        user_id = message.from_user.id
        lang = get_user_language(user_id)
        
        # Получаем информацию о подключении
        connection = db.bits_user_connection.find_one({
            '_id': ObjectId(connection_id),
            'user_id': user_id
        })
        
        if connection:
            # Возвращаем пользователя к информации о подключении
            bot.edit_message_text(
                TEXTS[lang]['connection_info'].format(**connection),
                message.chat.id,
                message.message_id,
                reply_markup=create_connection_menu(connection, lang)
            )
        
    except Exception as e:
        logger.error(f"Ошибка при отмене удаления: {e}", exc_info=True)

def create_back_to_menu_button(lang: str) -> InlineKeyboardButton:
    """Создает кнопку возврата в главное меню"""
    bot.send_message(
        message.chat.id,
        section_text,
        parse_mode='HTML',
        reply_markup=create_info_menu_status(lang)
    )
    return "info_sent"


def create_info_menu_status(lang='en'):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    menu_buttons = {
        'ru': [
            ("📊 Стратегия", "strategy"),
            ("💱 Криптобиржи", "exchanges"),
            ("🔐 Безопасность", "security"),
            ("💰 Взаиморасчеты", "payments"),
            ("💎 Доп. доходы", "extraincome"),
            ("🔗 Как подключиться?", "howtoconnect"),
            ("⬅️ Назад", "back")
        ],
        'en': [
            ("📊 Strategy", "strategy"),
            ("💱 Crypto Exchanges", "exchanges"),
            ("🔐 Security", "security"),
            ("💰 Payments", "payments"),
            ("💎 Extra Income", "extraincome"),
            ("🔗 How to Connect?", "howtoconnect"),
            ("⬅️ Back", "back")
        ],
        'fra': [
            ("📊 Stratégie", "strategy"),
            ("💱 Exchanges Crypto", "exchanges"),
            ("🔐 Sécurité", "security"),
            ("💰 Paiements", "payments"),
            ("💎 Revenus Extras", "extraincome"),
            ("🔗 Comment se Connecter?", "howtoconnect"),
            ("⬅️ Retour", "back")
        ],
        'deu': [
            ("📊 Strategie", "strategy"),
            ("💱 Kryptobörsen", "exchanges"),
            ("🔐 Sicherheit", "security"),
            ("💰 Zahlungen", "payments"),
            ("💎 Zusätzliches Einkommen", "extraincome"),
            ("🔗 Wie verbinden?", "howtoconnect"),
            ("⬅️ Zurück", "back")
        ],
        'esp': [
            ("📊 Estrategia", "strategy"),
            ("💱 Exchanges de Cripto", "exchanges"),
            ("🔐 Seguridad", "security"),
            ("💰 Pagos", "payments"),
            ("💎 Ingresos Extra", "extraincome"),
            ("🔗 ¿Cómo Conectarse?", "howtoconnect"),
            ("⬅️ Volver", "back")
        ],
        'lang_zh': [
            ("📊 策略", "strategy"),
            ("💱 加密货币交易所", "exchanges"),
            ("🔐 安全", "security"),
            ("💰 支付", "payments"),
            ("💎 额外收入", "extraincome"),
            ("🔗 如何连接？", "howtoconnect"),
            ("⬅️ 返回", "back")
        ]
    }
    
    buttons = menu_buttons.get(lang, menu_buttons['en'])
    # Создаем все кнопки кроме последней (Назад) по две в ряд
    for i in range(0, len(buttons) - 1, 2):
        row_buttons = []
        for j in range(2):
            if i + j < len(buttons) - 1:  # Проверяем, чтобы не добавить кнопку "Назад"
                text, callback = buttons[i + j]
                row_buttons.append(types.InlineKeyboardButton(text, callback_data=f"info_{callback}"))
        markup.row(*row_buttons)
    
    # Добавляем кнопку "Назад" отдельной строкой
    back_text, back_callback = buttons[-1]
    markup.row(types.InlineKeyboardButton(back_text, callback_data=f"info_{back_callback}"))
    
    return markup

