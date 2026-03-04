import telebot
from telebot import types
import sqlite3
import os
import config

bot = telebot.TeleBot(config.TOKEN)

# Путь к базе данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'empire_data.db')

# --- ИНИЦИАЛИЗАЦИЯ БД ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Добавлена колонка has_gold для учета купленных скинов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance INTEGER DEFAULT 0,
            current_skin TEXT DEFAULT 'Classic Snake',
            has_gold INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT balance, current_skin, has_gold FROM users WHERE user_id = ?', (user_id,))
    data = cursor.fetchone()
    conn.close()
    return data if data else (0, 'Classic Snake', 0)

init_db()

# --- КОМАНДА START ---
@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, current_skin, has_gold) VALUES (?, ?, ?, 0)', 
                   (message.from_user.id, message.from_user.first_name, 'Classic Snake'))
    conn.commit()
    conn.close()

    balance, skin, _ = get_user_data(message.from_user.id)
    skin_param = skin.replace(" ", "_")

    markup_reply = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_url = f"https://snickround.github.io/SnakeEmpire/?skin={skin_param}"
    web_app = types.WebAppInfo(web_app_url)
    btn_start_game = types.KeyboardButton("🐍 Играть в Empire", web_app=web_app)
    markup_reply.add(btn_start_game)

    markup_inline = types.InlineKeyboardMarkup()
    markup_inline.add(types.InlineKeyboardButton("👤 Мой Профиль", callback_data="profile"))
    markup_inline.add(types.InlineKeyboardButton("🛍️ Магазин скинов", callback_data="shop"))
    markup_inline.add(types.InlineKeyboardButton("🏆 Топ Игроков", callback_data="leaderboard"))
    
    bot.send_message(message.chat.id, 
                     f"Привет, {message.from_user.first_name}! 🚀\n\n"
                     f"Добро пожаловать в Snake Empire: Crypto Evolution.\n"
                     f"Здесь ты превращаешь очки в активы и строишь свою империю.\n\n"
                     f"Жми на кнопку ниже, чтобы начать!\n"
                     f"(Чтобы монеты СОХРАНЯЛИСЬ, жми на большую кнопку внизу клавиатуры!)\n\n"
                     f"💰 Твой баланс: {balance} MONEY", 
                     reply_markup=markup_reply)
    bot.send_message(message.chat.id, "Управление империей:", reply_markup=markup_inline)

# --- ПРОФИЛЬ ---
@bot.callback_query_handler(func=lambda call: call.data == "profile")
def profile(call):
    balance, skin, _ = get_user_data(call.from_user.id)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, 
                     f"👤 Профиль: {call.from_user.first_name}\n💰 Кошелек: {balance} MONEY\n🐍 Скин: {skin}")

# --- МАГАЗИН ---
@bot.callback_query_handler(func=lambda call: call.data == "shop")
def shop(call):
    balance, current_skin, has_gold = get_user_data(call.from_user.id)
    bot.answer_callback_query(call.id)
    
    text = (f"🏪 **Магазин Скинов**\n\n"
            f"💰 Твой баланс: {balance} MONEY\n"
            f"🐍 Сейчас надет: *{current_skin}*\n\n"
            f"Выбери скин:")
    
    markup = types.InlineKeyboardMarkup()
    
    # Кнопка для Classic
    if current_skin == "Classic Snake":
        markup.add(types.InlineKeyboardButton("✅ Classic (Надето)", callback_data="none"))
    else:
        markup.add(types.InlineKeyboardButton("✨ Надеть Classic", callback_data="set_classic"))
        
    # Логика для Gold Genesis
    if has_gold == 1:
        if current_skin == "Gold Genesis":
            markup.add(types.InlineKeyboardButton("✅ Gold (Надето)", callback_data="none"))
        else:
            markup.add(types.InlineKeyboardButton("✨ Надеть Gold Genesis", callback_data="set_gold"))
    else:
        markup.add(types.InlineKeyboardButton("💰 Купить Gold (1000)", callback_data="buy_gold"))
    
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

# Установка скинов
@bot.callback_query_handler(func=lambda call: call.data in ["set_classic", "set_gold"])
def set_skin(call):
    new_skin = "Classic Snake" if call.data == "set_classic" else "Gold Genesis"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET current_skin = ? WHERE user_id = ?', (new_skin, call.from_user.id))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, f"🐍 {new_skin} надет!")
    bot.send_message(call.message.chat.id, "✨ Нажми /start, чтобы обновить скин!")
    shop(call) # Обновляем меню

@bot.callback_query_handler(func=lambda call: call.data == "buy_gold")
def buy_gold(call):
    balance, _, _ = get_user_data(call.from_user.id)
    if balance < 1000:
        bot.answer_callback_query(call.id, "❌ Недостаточно MONEY!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance - 1000, current_skin = "Gold Genesis", has_gold = 1 WHERE user_id = ?', (call.from_user.id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "🔥 Gold Genesis разблокирован!")
    bot.send_message(call.message.chat.id, "✨ Поздравляем!\nСкин Gold Genesis установлен. Нажми /start, чтобы обновить скин!")
    shop(call)

# --- ПРИЕМ ДАННЫХ ИЗ ИГРЫ ---
@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    try:
        coins = int(message.web_app_data.data)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (coins, message.from_user.id))
        conn.commit()
        conn.close()
        
        # ВОТ ТУТ МЫ ДОБАВЛЯЕМ ПОЛУЧЕНИЕ ДАННЫХ
        # Нам нужно вытащить новый баланс из базы, чтобы показать его пользователю
        balance, _, _ = get_user_data(message.from_user.id)
        
        bot.send_message(message.chat.id, 
                         f"🎮 Очки сохранены!\n"
                         f"💰 +{coins} MONEY\n"
                         f"📈 Итого: {balance} MONEY")
    except Exception as e:
        print(f"Ошибка в web_app_data_handler: {e}")

# --- ЛИДЕРБОРД ---
# Функция для получения лидеров
def get_leaderboard():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Выбираем топ 5 игроков по балансу
    cursor.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 5')
    leaders = cursor.fetchall()
    conn.close()
    return leaders

# Обработчик кнопки Топ Игроков
@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def leaderboard(call):
    leaders = get_leaderboard()
    bot.answer_callback_query(call.id)
    
    text = "🏆 **ТОП-5 МАГНАТОВ EMPIRE**\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, user in enumerate(leaders):
        username = user[0] if user[0] else "Аноним"
        balance = user[1]
        text += f"{medals[i]} {username}: {balance} MONEY\n"
    
    text += "\nСтань первым в списке! 🚀"
    
    bot.send_message(call.message.chat.id, text, parse_mode="Markdown")

# --- Админский чит-код ---
@bot.message_handler(commands=['give_money'])
def give_money(message):
    # В идеале тут стоит проверка на твой user_id, чтобы обычные игроки не хитрили
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + 5000 WHERE user_id = ?', (message.from_user.id,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "💰 Казна пополнена на 5000 MONEY!")

bot.polling(none_stop=True)