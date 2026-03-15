import asyncio
import random
import time
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
API_TOKEN = '8751988721:AAFsInkEixk90cN0tiYZgE_s4eVWZSU7pnY'
COOLDOWN_SECONDS = 4 * 3600

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, last_open INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user(user_id, username):
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, last_open FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        cursor.execute("INSERT INTO users (user_id, username, balance, last_open) VALUES (?, ?, 0, 0)", (user_id, username))
        conn.commit()
        res = (0, 0)
    conn.close()
    return {"balance": res[0], "last_open": res[1]}

def update_user(user_id, balance, last_open):
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ?, last_open = ? WHERE user_id = ?", (balance, last_open, user_id))
    conn.commit()
    conn.close()

def get_rank(balance):
    if balance < 1000: return "Новичок 🌱"
    if balance < 5000: return "Делец 💼"
    if balance < 20000: return "Магнат 🎩"
    return "Акула TON 🦈"

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    get_user(message.from_user.id, message.from_user.first_name)
    await message.answer(f"Привет, пупсик! 👋\nКоманды:\n/loot — открыть кейс\n/profile — твой опыт и ранг\n/top — таблица лидеров")

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    await message.answer(
        f"👤 Профиль: {message.from_user.first_name}\n"
        f"💵 Опыт: {user['balance']}$\n"
        f"🏆 Ранг: {get_rank(user['balance'])}"
    )

@dp.message(Command("loot"))
async def cmd_loot(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id, message.from_user.first_name)
    now = int(time.time())

    if now - user['last_open'] < COOLDOWN_SECONDS:
        rem = COOLDOWN_SECONDS - (now - user['last_open'])
        await message.answer(f"⏳ Рано! Приходи через {rem // 3600}ч. {(rem % 3600) // 60}мин.")
        return

    # Логика выпадения
    loot = random.randint(15, 70)
    is_crit = random.random() < 0.1
    if is_crit: loot *= 5

    new_balance = user['balance'] + loot
    update_user(user_id, new_balance, now)

    msg = f"🔥 КРИТ! +{loot}$" if is_crit else f"💵 Нашел +{loot}$"
    await message.answer(f"{msg}\nТеперь у тебя: {new_balance}$")

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    conn = sqlite3.connect('game.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    text = "🏆 **ТОП МАГНАТОВ** 🏆\n\n"
    for i, row in enumerate(rows, 1):
        text += f"{i}. {row[0]} — {row[1]}$\n"
    await message.answer(text, parse_mode="Markdown")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
