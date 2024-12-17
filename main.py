from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
import sqlite3
import asyncio

# API для получения данных
API_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"

# Функция для инициализации базы данных
def init_db():
    #Соединяет с базой данных, если базы не существует, создается new
    conn = sqlite3.connect("users.db")

    cursor = conn.cursor() #Объект курсора для создания sql запросов
    
    # Выполняет sql запрос, создаёт таблицу, вставляет данные, обновляет записи и выполняет SELECT-запросы.
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            preferred_crypto TEXT DEFAULT 'bitcoin'
        )
    ''')
    conn.commit() # cохраняет изменеия в базе 
    conn.close()

# Сохранение настроек пользователя
def save_user_settings(user_id, crypto):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, preferred_crypto)
        VALUES (?, ?)
    ''', (user_id, crypto))
    conn.commit()
    conn.close()

# Получение настроек пользователя
def get_user_settings(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('SELECT preferred_crypto FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 'bitcoin'

# Функция для получения данных о криптовалютах
def get_crypto_data(crypto):
    try:
        response = requests.get(API_URL) # Выполняет HTTP запрос
        response.raise_for_status()  # Проверка на успешный запрос
        data = response.json() # json -> python
        return data.get(crypto, {}).get('usd', "Данные не найдены")
    except requests.exceptions.RequestException as e:
        return f"Ошибка запроса: {e}"

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id # Представляет данные о входящем обновлении (сообщении, кнопке, команде и т. д.), полученном ботом.
    save_user_settings(user_id, 'bitcoin')  # По умолчанию

    # Текст приветствия
    message = (
        "👋 Добро пожаловать в бот-криптоассистент! Вот что я умею:\n\n"
        "📊 **Доступные команды:**\n"
        "/start - Отобразить это сообщение\n"
        "/price - Узнать текущую цену выбранной криптовалюты\n"
        "/settings - Выбрать криптовалюту для отслеживания (Bitcoin или Ethereum)\n\n"
        "💡 **Как я работаю:**\n"
        "Я помогаю вам узнавать текущие цены популярных криптовалют (Bitcoin и Ethereum). "
        "Если вы ошиблись в команде, я подскажу, как исправить ошибку.\n\n"
        "💬 Введите одну из команд выше, чтобы начать!"
    )

    await update.message.reply_text(message)


# Обработчик команды /price
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    crypto = get_user_settings(user_id)
    price = get_crypto_data(crypto)
    await update.message.reply_text(f"Текущая цена {crypto.capitalize()}: ${price}")

# Обработчик команды /settings
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Bitcoin", callback_data='bitcoin')],
        [InlineKeyboardButton("Ethereum", callback_data='ethereum')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите криптовалюту для отслеживания:", reply_markup=reply_markup)

# Callback для обработки выбора валюты
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    save_user_settings(user_id, query.data)
    await query.edit_message_text(f"Ваш выбор сохранён: {query.data.capitalize()}")

# Обработчик неизвестных сообщений
async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Извините, я вас не понимаю. Я всего лишь бот и могу реагировать только на команды. "
        "Попробуйте одну из доступных команд, например /start, чтобы узнать, что я умею."
    )

# Основной блок
if __name__ == '__main__':
    # Инициализация базы данных
    init_db()

    # Считывание токена из файла
    with open("token.txt") as f:
        BOT_TOKEN = f.read()

    # Создание приложения Telegram
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("price", get_price))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # Запуск бота
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    try:
        asyncio.run(application.run_polling(stop_signals=None))
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")