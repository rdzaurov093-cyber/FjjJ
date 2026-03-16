import asyncio
import random
import time
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ (ВСТАВЬ СВОЙ ТОКЕН) ---
API_TOKEN = '8751988721:AAFsInkEixk90cN0tiYZgE_s4eVWZSU7pnY'
COOLDOWN_LOOT = 600       # 10 минут
WORKER_PRICE = 1000       # Цена рабочего
WORKER_PROFIT = 100       # Доход рабочего в час

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- СЛОВАРЬ ПОДАРКОВ ---
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
    "Ты выглядишь потрясающе! 😍", "У тебя прекрасная улыбка! ✨",
    "С тобой так тепло и уютно. 🌸", "Твои глаза просто космос! 🌌",
    "Ты невероятно умный(ая)! 🧠", "Твоя энергия заряжает позитивом! ⚡️"
]

# Глобальный словарь для игры в мины
g_m = {}

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    # Таблица пользователей
    cur.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY, name TEXT, username TEXT, exp INTEGER DEFAULT 0, 
                   last_loot INTEGER DEFAULT 0, last_bonus INTEGER DEFAULT 0,
                   workers INTEGER DEFAULT 0, last_collect INTEGER DEFAULT 0, partner_id INTEGER DEFAULT 0)''')
    # Таблица инвентаря
    cur.execute('''CREATE TABLE IF NOT EXISTS inventory 
                  (user_id INTEGER, item_id TEXT, amount INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

def get_user(user: types.User):
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    cur.execute("SELECT exp, last_loot, last_bonus, workers, last_collect, partner_id, name, username FROM users WHERE id = ?", (user.id,))
    res = cur.fetchone()
    uname = user.username.lower() if user.username else ""
    if not res:
        now = int(time.time())
        cur.execute("INSERT INTO users (id, name, username, exp, last_collect) VALUES (?, ?, ?, 0, ?)", 
                    (user.id, user.first_name, uname, now))
        conn.commit()
        res = (0, 0, 0, 0, now, 0, user.first_name, uname)
    conn.close()
    return res

def get_inventory_profit(user_id):
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT item_id, amount FROM inventory WHERE user_id = ?", (user_id,))
    rows = cur.fetchall(); conn.close()
    total_profit = 0; items_list = []
    for item_id, amount in rows:
        if item_id in GIFTS:
            total_profit += GIFTS[item_id]['profit'] * amount
            items_list.append(f"{GIFTS[item_id]['emoji']} {GIFTS[item_id]['name']} (x{amount})")
    return total_profit, items_list

# --- ОСНОВНЫЕ КОМАНДЫ ---

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
    await m.reply(f"<b>Привет, {m.from_user.first_name}!</b> 👋\nТвой бизнес ждет тебя. Используй меню или команды.", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    u = get_user(m.from_user)
    p_name = "Одинок(а) 💨"
    if u[5]:
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("SELECT name FROM users WHERE id = ?", (u[5],))
        res = cur.fetchone(); conn.close()
        if res: p_name = f"В браке с <b>{res[0]}</b> ❤️"

    profit, items = get_inventory_profit(m.from_user.id)
    inv_text = "\n".join(items) if items else "Пусто"
    
    text = (f"👤 <b>Профиль: {m.from_user.first_name}</b>\n"
            f"💍 Статус: {p_name}\n\n"
            f"💵 Баланс: <b>{u[0]} $</b>\n"
            f"👷 Рабочих: <b>{u[3]}</b>\n\n"
            f"🎒 <b>Инвентарь:</b>\n{inv_text}")
    await m.reply(text, parse_mode="HTML")

# --- СИСТЕМА ПОДАРКОВ ---

@dp.message(Command("gift"))
async def cmd_gift(m: types.Message, command: CommandObject):
    if not command.args:
        text = "🎁 <b>Магазин подарков (купить по ID):</b>\n\n"
        for idx, v in GIFTS.items():
            text += f"<code>{idx}</code>. {v['emoji']} {v['name']} — {v['price']}$ (+{v['profit']}$/ч)\n"
        text += "\nПример ответом: <code>/gift 1</code>\nПример по юзеру: <code>/gift @user 1</code>"
        return await m.reply(text, parse_mode="HTML")

    args = command.args.split()
    item_id = args[-1]
    if item_id not in GIFTS: return await m.reply("❌ Неверный ID!")

    if m.reply_to_message:
        target_id, target_name = m.reply_to_message.from_user.id, m.reply_to_message.from_user.first_name
    else:
        if len(args) < 2: return await m.reply("❌ Укажи @user и ID.")
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("SELECT id, name FROM users WHERE username = ?", (args[0].replace('@','').lower(),))
        t = cur.fetchone(); conn.close()
        if not t: return await m.reply("❌ Юзер не найден!")
        target_id, target_name = t

    u = get_user(m.from_user)
    gift = GIFTS[item_id]
    if u[0] < gift['price']: return await m.reply("❌ Не хватает денег!")

    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (gift['price'], m.from_user.id))
    cur.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (target_id, item_id))
    if cur.fetchone(): cur.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id = ? AND item_id = ?", (target_id, item_id))
    else: cur.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (target_id, item_id))
    conn.commit(); conn.close()
    await m.reply(f"🎁 Ты подарил(а) <b>{target_name}</b> {gift['emoji']} {gift['name']}!", parse_mode="HTML")

@dp.message(Command("giftlove"))
async def cmd_giftlove(m: types.Message, command: CommandObject):
    u = get_user(m.from_user)
    if not u[5]: return await m.reply("❌ Ты не в браке!")
    if not command.args or command.args not in GIFTS: return await m.reply("❌ Укажи верный ID.")
    
    gift = GIFTS[command.args]
    if u[0] < gift['price']: return await m.reply("❌ Нет денег!")

    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (gift['price'], m.from_user.id))
    cur.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (u[5], command.args))
    if cur.fetchone(): cur.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id = ? AND item_id = ?", (u[5], command.args))
    else: cur.execute("INSERT INTO inventory (user_id, item_id, amount) VALUES (?, ?, 1)", (u[5], command.args))
    conn.commit(); conn.close()
    await m.reply(f"💝 Подарок {gift['emoji']} отправлен половинке!", parse_mode="HTML")

# --- БИЗНЕС ---

@dp.message(Command("business", "bussines"))
async def business(m: types.Message):
    u = get_user(m.from_user)
    g_p, _ = get_inventory_profit(m.from_user.id)
    g_p = min(400, g_p)
    total = (u[3] * WORKER_PROFIT) + g_p
    await m.reply(f"🏢 <b>Бизнес</b>\n👥 Рабочих: {u[3]} ({u[3]*WORKER_PROFIT}$/ч)\n🎁 Подарки: {g_p}$/ч\n💰 Итого: {total}$/ч", parse_mode="HTML")

@dp.message(Command("collect"))
async def collect(m: types.Message):
    u = get_user(m.from_user); now = int(time.time())
    hrs = (now - u[4]) // 3600
    if hrs < 1: return await m.reply("⏳ Копим минимум час!")
    g_p, _ = get_inventory_profit(m.from_user.id)
    total = hrs * ((u[3] * WORKER_PROFIT) + min(400, g_p))
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp + ?, last_collect = ? WHERE id = ?", (total, now, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply(f"📥 Собрано прибыли: <b>{total}$</b>", parse_mode="HTML")

# --- РПГ И ТРИГГЕРЫ ---

@dp.message(Command("hug", "kiss", "slap", "fuck"))
async def cmd_rpg(m: types.Message):
    acts = {"hug": ("🫂", "обнял(а)"), "kiss": ("💋", "поцеловал(а)"), "slap": ("👊", "дал(а) леща"), "fuck": ("🔞", "оттрахал(а)")}
    cmd = m.text[1:].split()[0]
    e, txt = acts[cmd]
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else "воздух"
    await m.reply(f"<b>{m.from_user.first_name}</b> {e} {txt} <b>{target}</b>", parse_mode="HTML")

@dp.message(F.text.lower().in_({"поцеловать", "кусь", "оттрахать", "куни", "минет", "ласкать щеку"}))
async def text_rpg(m: types.Message):
    acts = {"поцеловать": ("💋", "поцеловал(а)"), "кусь": ("🦷", "сделал(а) кусь"), "оттрахать": ("🔞", "оттрахал(а)"), "куни": ("👅", "сделал(а) куни"), "минет": ("🍌", "сделал(а) минет"), "ласкать щеку": ("🥰", "поласкал(а) щеку")}
    e, txt = acts[m.text.lower()]
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else "воздух"
    await m.reply(f"<b>{m.from_user.first_name}</b> {e} {txt} <b>{target}</b>", parse_mode="HTML")

@dp.message(F.text.lower() == "сделать комплимент")
async def compl(m: types.Message):
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else "себе"
    await m.reply(f"<b>{m.from_user.first_name}</b> 💬 <b>{target}</b>: {random.choice(COMPLIMENTS)}", parse_mode="HTML")

# --- БРАКИ И РАЗВОДЫ ---

@dp.message(Command("marry"))
async def cmd_marry(m: types.Message):
    if not m.reply_to_message: return await m.reply("Ответь на сообщение партнера!")
    u, t = get_user(m.from_user), get_user(m.reply_to_message.from_user)
    if u[5] or t[5]: return await m.reply("Кто-то уже занят! 💔")
    kb = InlineKeyboardBuilder()
    kb.button(text="Да ❤️", callback_data=f"ma_y_{m.reply_to_message.from_user.id}_{m.from_user.id}")
    kb.button(text="Нет 💔", callback_data=f"ma_n_{m.reply_to_message.from_user.id}_{m.from_user.id}")
    await m.reply(f"💍 {m.reply_to_message.from_user.first_name}, согласны на брак?", reply_markup=kb.as_markup())

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
    else: await c.message.edit_text("💔 Увы, отказ.")

@dp.message(Command("divorce"))
async def divorce(m: types.Message):
    u = get_user(m.from_user)
    if not u[5]: return await m.reply("Ты не в браке!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET partner_id = 0 WHERE id = ?", (m.from_user.id,))
    cur.execute("UPDATE users SET partner_id = 0 WHERE id = ?", (u[5],))
    conn.commit(); conn.close(); await m.reply("💔 Развод оформлен.")

# --- ИГРА МИНЫ ---

@dp.message(Command("min"))
async def mines(m: types.Message):
    f = [0]*21 + [1]*4; random.shuffle(f)
    g_m[m.from_user.id] = {"f": f, "s": 5, "w": 0, "o": []}
    kb = InlineKeyboardBuilder()
    for i in range(25): kb.button(text="❓", callback_data=f"mi_{i}")
    await m.reply("💣 <b>Минное поле (5 ходов):</b>", reply_markup=kb.adjust(5).as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("mi_"))
async def mi_cb(c: types.CallbackQuery):
    uid = c.from_user.id
    if uid not in g_m: return
    idx = int(c.data.split("_")[1]); g = g_m[uid]
    if idx in g["o"]: return
    g["s"] -= 1; g["o"].append(idx)
    if g["f"][idx] == 0: g["w"] += random.randint(20, 60)
    if g["s"] > 0:
        kb = InlineKeyboardBuilder()
        for i in range(25): kb.button(text="❓" if i not in g["o"] else ("💣" if g["f"][i] else "✅"), callback_data=f"mi_{i}")
        await c.message.edit_text(f"Собрано: {g['w']}$ | Ходов: {g['s']}", reply_markup=kb.adjust(5).as_markup())
    else:
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (g['w'], uid)); conn.commit(); conn.close()
        await c.message.edit_text(f"🏁 Итог игры: <b>+{g['w']}$</b>", parse_mode="HTML"); del g_m[uid]

# --- ПРОЧЕЕ ---

@dp.message(Command("top"))
async def top(m: types.Message):
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT name, exp FROM users ORDER BY exp DESC LIMIT 10")
    rows = cur.fetchall(); conn.close()
    txt = "🏆 <b>ТОП МАГНАТОВ</b>\n\n"
    for i, r in enumerate(rows, 1): txt += f"{i}. {r[0]} — {r[1]}$\n"
    await m.reply(txt, parse_mode="HTML")

@dp.message(Command("ref"))
async def ref(m: types.Message):
    me = await bot.get_me()
    await m.reply(f"🔗 Твоя ссылка:\n<code>https://t.me/{me.username}?start={m.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("loot"))
async def cmd_loot(m: types.Message):
    u = get_user(m.from_user); now = int(time.time())
    if now - u[1] < COOLDOWN_LOOT: return await m.reply("⏳ Подожди 10 минут!")
    win = random.randint(50, 200)
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp + ?, last_loot = ? WHERE id = ?", (win, now, m.from_user.id))
    conn.commit(); conn.close(); await m.reply(f"📦 Кейс: <b>+{win}$</b>", parse_mode="HTML")

@dp.message(Command("hire"))
async def hire(m: types.Message):
    u = get_user(m.from_user)
    if u[0] < WORKER_PRICE: return await m.reply("❌ Мало денег!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ?, workers = workers + 1 WHERE id = ?", (WORKER_PRICE, m.from_user.id))
    conn.commit(); conn.close(); await m.reply("👷 Рабочий нанят!")

@dp.message(Command("pay"))
async def pay(m: types.Message, command: CommandObject):
    if not command.args or len(command.args.split()) < 2: return await m.reply("Пример: /pay @user 100")
    un = command.args.split()[0].replace('@', '').lower(); amt = int(command.args.split()[1])
    u = get_user(m.from_user)
    if u[0] < amt or amt <= 0: return await m.reply("❌ Ошибка суммы!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (un,))
    t = cur.fetchone()
    if not t: return await m.reply("❌ Юзер не найден!")
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (amt, m.from_user.id))
    cur.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amt, t[0]))
    conn.commit(); conn.close(); await m.reply(f"✅ Переведено {amt}$ для @{un}")

async def main():
    init_db(); print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
