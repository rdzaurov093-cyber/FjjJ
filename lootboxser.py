import asyncio
import random
import time
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
API_TOKEN = '8751988721:AAFsInkEixk90cN0tiYZgE_s4eVWZSU7pnY'
COOLDOWN_LOOT = 10 * 60  # 10 минут
WORKER_PRICE = 1000  
WORKER_PROFIT = 100  

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- СПИСОК ПОДАРКОВ (ID: Данные) ---
GIFTS = {
    "1": {"price": 699, "profit": 50, "emoji": "📱", "name": "Айфон"},
    "2": {"price": 300, "profit": 20, "emoji": "💻", "name": "МакБук"},
    "3": {"price": 250, "profit": 15, "emoji": "💻", "name": "Ноутбук"},
    "4": {"price": 500, "profit": 35, "emoji": "🖥", "name": "Игровой Компьютер"},
    "5": {"price": 1100, "profit": 100, "emoji": "🚗", "name": "Автомобиль"},
    "6": {"price": 2000, "profit": 200, "emoji": "💍", "name": "Кольцо с бриллиантом"},
    "7": {"price": 5000, "profit": 400, "emoji": "🛥", "name": "Яхта"}
}

COMPLIMENTS = [
    "Ты выглядишь потрясающе! 😍",
    "У тебя прекрасная улыбка! ✨",
    "С тобой так тепло и уютно. 🌸",
    "Твои глаза просто космос! 🌌",
    "Ты невероятно умный(ая) и интересный(ая)! 🧠",
    "Твоя энергия заряжает позитивом! ⚡️",
    "Ты делаешь этот мир лучше одним своим присутствием. 🌍",
    "У тебя безупречный вкус! 👗👔",
    "Ты просто золото! 🏆",
    "Каждое мгновение с тобой — праздник! 🎉"
]

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY, name TEXT, username TEXT, exp INTEGER DEFAULT 0, 
                   last_loot INTEGER DEFAULT 0, last_bonus INTEGER DEFAULT 0,
                   workers INTEGER DEFAULT 0, last_collect INTEGER DEFAULT 0, partner_id INTEGER DEFAULT 0)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS inventory 
                  (user_id INTEGER, item_id TEXT, amount INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user(user: types.User):
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT exp, last_loot, last_bonus, workers, last_collect, partner_id, name, username FROM users WHERE id = ?", (user.id,))
    res = cur.fetchone()
    uname = user.username.lower() if user.username else ""
    if not res:
        now = int(time.time())
        cur.execute("INSERT INTO users (id, name, username, exp, last_collect) VALUES (?, ?, ?, 0, ?)", 
                    (user.id, user.first_name, uname, now))
        conn.commit()
        res = (0, 0, 0, 0, now, 0, user.first_name, uname)
    else:
        if res[7] != uname:
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (uname, user.id))
            conn.commit()
    conn.close()
    return res

def get_inventory_profit(user_id):
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT item_id, amount FROM inventory WHERE user_id = ?", (user_id,))
    rows = cur.fetchall(); conn.close()
    total_profit = 0
    items_list = []
    for item_id, amount in rows:
        if item_id in GIFTS:
            total_profit += GIFTS[item_id]['profit'] * amount
            items_list.append(f"{GIFTS[item_id]['emoji']} {GIFTS[item_id]['name']} (x{amount})")
    return total_profit, items_list

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message, command: CommandObject):
    get_user(m.from_user)
    if command.args and command.args.isdigit() and int(command.args) != m.from_user.id:
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET exp = exp + 500 WHERE id = ?", (int(command.args),))
        cur.execute("UPDATE users SET exp = exp + 200 WHERE id = ?", (m.from_user.id,))
        conn.commit(); conn.close()
        try: await bot.send_message(int(command.args), "💎 Друг пришел по ссылке! <b>+500$</b>", parse_mode="HTML")
        except: pass
    await m.reply(f"<b>Привет, {m.from_user.first_name}!</b> 👋\nТвой бизнес ждет тебя.", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    u = get_user(m.from_user)
    status = f"В браке с ❤️" if u[5] else "Одинок(а) 💨"
    if u[5]:
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM users WHERE id = ?", (u[5],))
        p = cur.fetchone(); conn.close()
        status = f"В браке с <b>{p[0]}</b> ❤️" if p else status

    _, items = get_inventory_profit(m.from_user.id)
    inv_text = "\n".join(items) if items else "Пусто"

    text = (
        f"👤 <b>Профиль: {m.from_user.first_name}</b>\n"
        f"💍 Статус: {status}\n\n"
        f"💵 Баланс: <b>{u[0]} $</b>\n"
        f"👷 Рабочих: <b>{u[3]}</b>\n\n"
        f"🎒 <b>Инвентарь:</b>\n{inv_text}"
    )
    await m.reply(text, parse_mode="HTML")

# --- СИСТЕМА ПОДАРКОВ ---

@dp.message(Command("gift"))
async def cmd_gift(m: types.Message, command: CommandObject):
    if not command.args:
        text = "🎁 <b>Магазин подарков:</b>\n\n"
        for idx, v in GIFTS.items():
            text += f"<code>{idx}</code>. {v['emoji']} {v['name']} — {v['price']}$ (+{v['profit']}$/ч)\n"
        text += "\nИспользование:\nОтветом: <code>/gift ID</code>\nПо юзеру: <code>/gift @user ID</code>"
        return await m.reply(text, parse_mode="HTML")

    args = command.args.split()
    item_id = args[-1]
    if item_id not in GIFTS: return await m.reply("❌ Неверный ID подарка!")

    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
        target_name = m.reply_to_message.from_user.first_name
    else:
        if len(args) < 2: return await m.reply("❌ Укажи @юзернейм и ID!")
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("SELECT id, name FROM users WHERE username = ?", (args[0].replace('@','').lower(),))
        t = cur.fetchone(); conn.close()
        if not t: return await m.reply("❌ Юзер не найден!")
        target_id, target_name = t

    gift = GIFTS[item_id]
    u = get_user(m.from_user)
    if u[0] < gift['price']: return await m.reply("❌ Не хватает денег!")

    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (gift['price'], m.from_user.id))
    cur.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1) ON CONFLICT(user_id) DO UPDATE SET amount = amount + 1", (target_id, item_id))
    # Для упрощения без ON CONFLICT (зависит от версии sqlite):
    cur.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (target_id, item_id))
    if cur.fetchone(): cur.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id = ? AND item_id = ?", (target_id, item_id))
    else: cur.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (target_id, item_id))
    conn.commit(); conn.close()
    await m.reply(f"🎁 Ты подарил(а) <b>{target_name}</b> {gift['emoji']} {gift['name']}!", parse_mode="HTML")

@dp.message(Command("giftlove"))
async def cmd_giftlove(m: types.Message, command: CommandObject):
    u = get_user(m.from_user)
    if not u[5]: return await m.reply("❌ Ты не в браке!")
    if not command.args or command.args not in GIFTS: return await m.reply("❌ Укажи верный ID!")
    
    gift = GIFTS[command.args]
    if u[0] < gift['price']: return await m.reply("❌ Недостаточно средств!")

    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (gift['price'], m.from_user.id))
    cur.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (u[5], command.args))
    if cur.fetchone(): cur.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id = ? AND item_id = ?", (u[5], command.args))
    else: cur.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (u[5], command.args))
    conn.commit(); conn.close()
    await m.reply(f"💝 Подарок {gift['emoji']} отправлен твоей половинке!", parse_mode="HTML")

# --- БИЗНЕС ---

@dp.message(Command("business"))
async def cmd_business(m: types.Message):
    u = get_user(m.from_user)
    g_profit, _ = get_inventory_profit(m.from_user.id)
    g_profit = min(400, g_profit)
    total = (u[3] * WORKER_PROFIT) + g_profit
    await m.reply(f"🏢 <b>Твой офис</b>\n👥 Рабочих: {u[3]}\n🎁 Доход с подарков: {g_profit}$/ч\n💰 Итого: {total}$/ч", parse_mode="HTML")

@dp.message(Command("collect"))
async def cmd_collect(m: types.Message):
    u = get_user(m.from_user); now = int(time.time())
    hrs = (now - u[4]) // 3600
    if hrs < 1: return await m.reply("⏳ Минимум через час!")
    
    g_p, _ = get_inventory_profit(m.from_user.id)
    total = hrs * ((u[3] * WORKER_PROFIT) + min(400, g_p))
    
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp + ?, last_collect = ? WHERE id = ?", (total, now, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply(f"📥 Собрано прибыль: <b>{total}$</b>", parse_mode="HTML")

# --- РПГ КЛЮЧЕВЫЕ СЛОВА ---

@dp.message(F.text.lower().in_({"поцеловать", "кусь", "оттрахать", "куни", "минет", "ласкать щеку", "сделать комплимент"}))
async def text_rpg_handler(m: types.Message):
    acts = {
        "поцеловать": ("💋", "поцеловал(а)"),
        "кусь": ("🦷", "сделал(а) кусь"),
        "оттрахать": ("🔞", "оттрахал(а)"),
        "куни": ("👅", "сделал(а) куни"),
        "минет": ("🍌", "сделал(а) минет"),
        "ласкать щеку": ("🥰", "поласкал(а) щеку")
    }
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else "воздух"
    
    if m.text.lower() == "сделать комплимент":
        res = f"<b>{m.from_user.first_name}</b> шепчет <b>{target}</b>:\n<i>{random.choice(COMPLIMENTS)}</i>"
    else:
        e, n = acts[m.text.lower()]
        res = f"<b>{m.from_user.first_name}</b> {e} {n} <b>{target}</b>"
    
    await m.reply(res, parse_mode="HTML")

# --- СТАНДАРТНЫЕ ФУНКЦИИ (ДЛЯ ЦЕЛОСТНОСТИ) ---

@dp.message(Command("loot"))
async def cmd_loot(m: types.Message):
    u = get_user(m.from_user); now = int(time.time())
    if now - u[1] < COOLDOWN_LOOT: return await m.reply("⏳ Рано!")
    win = random.randint(50, 200)
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp + ?, last_loot = ? WHERE id = ?", (win, now, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply(f"📦 Ты открыл кейс: <b>+{win}$</b>", parse_mode="HTML")

@dp.message(Command("hire"))
async def hire(m: types.Message):
    u = get_user(m.from_user)
    if u[0] < WORKER_PRICE: return await m.reply("❌ Нет денег!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ?, workers = workers + 1 WHERE id = ?", (WORKER_PRICE, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply("👷 Рабочий нанят!")

@dp.message(Command("pay"))
async def pay(m: types.Message, command: CommandObject):
    if not command.args or len(command.args.split()) < 2: return await m.reply("Пример: /pay @user 100")
    args = command.args.split()
    u = get_user(m.from_user); amt = int(args[1])
    if u[0] < amt or amt <= 0: return await m.reply("❌ Ошибка суммы!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (args[0].replace('@','').lower(),))
    t = cur.fetchone()
    if not t: return await m.reply("❌ Юзер не найден!")
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (amt, m.from_user.id))
    cur.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amt, t[0]))
    conn.commit(); conn.close()
    await m.reply(f"✅ Переведено {amt}$ для {args[0]}")

@dp.message(Command("marry"))
async def cmd_marry(m: types.Message):
    if not m.reply_to_message: return await m.reply("Ответь на сообщение партнера!")
    u, t = get_user(m.from_user), get_user(m.reply_to_message.from_user)
    if u[5] or t[5]: return await m.reply("Кто-то уже занят! 💔")
    kb = InlineKeyboardBuilder()
    kb.button(text="Да ❤️", callback_data=f"ma_y_{m.reply_to_message.from_user.id}_{m.from_user.id}")
    kb.button(text="Нет 💔", callback_data=f"ma_n_{m.reply_to_message.from_user.id}_{m.from_user.id}")
    await m.reply(f"💍 <b>{m.reply_to_message.from_user.first_name}</b>, согласны?", reply_markup=kb.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("ma_"))
async def marry_cb(c: types.CallbackQuery):
    _, act, tid, pid = c.data.split("_")
    if c.from_user.id != int(tid): return await c.answer("Не тебе!")
    if act == "y":
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET partner_id = ? WHERE id = ?", (tid, pid))
        cur.execute("UPDATE users SET partner_id = ? WHERE id = ?", (pid, tid))
        conn.commit(); conn.close()
        await c.message.edit_text("🥳 <b>Горько! Вы теперь пара!</b>", parse_mode="HTML")
    else: await c.message.edit_text("💔 Отказ...")

@dp.message(Command("top"))
async def top(m: types.Message):
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT name, exp FROM users ORDER BY exp DESC LIMIT 10")
    rows = cur.fetchall(); conn.close()
    txt = "🏆 <b>ТОП МАГНАТОВ</b>\n\n"
    for i, r in enumerate(rows, 1): txt += f"{i}. {r[0]} — {r[1]}$\n"
    await m.reply(txt, parse_mode="HTML")

async def main():
    init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
        
