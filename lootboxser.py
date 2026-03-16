import asyncio
import random
import time
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
API_TOKEN = '8751988721:AAFsInkEixk90cN0tiYZgE_s4eVWZSU7pnY'
COOLDOWN_LOOT = 10 * 600
COOLDOWN_BONUS = 24 * 3600
WORKER_PRICE = 1000  
WORKER_PROFIT = 100  

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- СПИСОК ПОДАРКОВ (ТЕПЕРЬ ПО ID) И КОМПЛИМЕНТОВ ---
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
    "Ты невероятно умный(ая) и интересный(ая) собеседник! 🧠",
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
    try:
        cur.execute("ALTER TABLE users ADD COLUMN partner_id INTEGER DEFAULT 0")
    except: pass
    
    # Таблица для инвентаря подарков
    cur.execute('''CREATE TABLE IF NOT EXISTS inventory 
                  (user_id INTEGER, item TEXT, amount INTEGER DEFAULT 0)''')
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
    else:
        if res[7] != uname:
            cur.execute("UPDATE users SET username = ? WHERE id = ?", (uname, user.id))
            conn.commit()
    conn.close()
    return res

def get_user_by_id(uid):
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    cur.execute("SELECT name, username FROM users WHERE id = ?", (uid,))
    res = cur.fetchone()
    conn.close()
    return res if res else ("Неизвестный", "")

def get_user_id_by_username(username):
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE username = ?", (username.replace('@', '').lower(),))
    res = cur.fetchone()
    conn.close()
    return res

def get_inventory_profit(user_id):
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    cur.execute("SELECT item, amount FROM inventory WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    
    total_profit = 0
    items_list = []
    for item, amount in rows:
        if item in GIFTS:
            total_profit += GIFTS[item]['profit'] * amount
            items_list.append(f"{GIFTS[item]['emoji']} {GIFTS[item]['name']} (x{amount})")
            
    return total_profit, items_list

def give_item(sender_id, receiver_id, price, item_id):
    conn = sqlite3.connect('loot.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (price, sender_id))
    cur.execute("SELECT amount FROM inventory WHERE user_id = ? AND item = ?", (receiver_id, item_id))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE inventory SET amount = amount + 1 WHERE user_id = ? AND item = ?", (receiver_id, item_id))
    else:
        cur.execute("INSERT INTO inventory (user_id, item, amount) VALUES (?, ?, 1)", (receiver_id, item_id))
    conn.commit()
    conn.close()

# --- КОМАНДЫ СТАРТ И ПРОФИЛЬ ---
@dp.message(Command("start"))
async def cmd_start(m: types.Message, command: CommandObject):
    u = get_user(m.from_user)
    if command.args and command.args.isdigit() and int(command.args) != m.from_user.id:
        if u[0] == 0:
            conn = sqlite3.connect('loot.db'); cur = conn.cursor()
            cur.execute("UPDATE users SET exp = exp + 500 WHERE id = ?", (int(command.args),))
            cur.execute("UPDATE users SET exp = exp + 200 WHERE id = ?", (m.from_user.id,))
            conn.commit(); conn.close()
            try: await bot.send_message(int(command.args), "💎 Друг пришел по ссылке! <b>+500$</b>", parse_mode="HTML")
            except: pass
    await m.reply(f"<b>Привет, {m.from_user.first_name}!</b> 👋\nТвой бизнес ждет тебя. Используй меню команд.", parse_mode="HTML")

@dp.message(Command("profile"))
async def cmd_profile(m: types.Message):
    u = get_user(m.from_user)
    status = "Одинок(а) 💨"
    if u[5] != 0:
        p_name, _ = get_user_by_id(u[5])
        status = f"В браке с <b>{p_name}</b> ❤️"
        
    _, items_list = get_inventory_profit(m.from_user.id)
    inv_text = "\n".join(items_list) if items_list else "Пусто"

    text = (
        f"👤 <b>Профиль: {m.from_user.first_name}</b>\n"
        f"🆔 ID: <code>{m.from_user.id}</code>\n"
        f"💍 Статус: {status}\n\n"
        f"💵 Баланс: <b>{u[0]} $</b>\n"
        f"👷 Рабочих: <b>{u[3]}</b>\n\n"
        f"🎒 <b>Инвентарь (Подарки):</b>\n{inv_text}"
    )
    await m.reply(text, parse_mode="HTML")

# --- СВАДЬБА И РАЗВОД ---
@dp.message(Command("marry"))
async def cmd_marry(m: types.Message):
    if not m.reply_to_message: return await m.reply("Ответь на сообщение партнера! 💍")
    u, t = get_user(m.from_user), get_user(m.reply_to_message.from_user)
    if u[5] or t[5]: return await m.reply("Кто-то уже в браке! 💔")
    if m.from_user.id == m.reply_to_message.from_user.id: return await m.reply("Нельзя жениться на себе! 😂")

    kb = InlineKeyboardBuilder()
    kb.button(text="Да, согласен(на) ❤️", callback_data=f"ma_y_{m.reply_to_message.from_user.id}_{m.from_user.id}")
    kb.button(text="Нет 💔", callback_data=f"ma_n_{m.reply_to_message.from_user.id}_{m.from_user.id}")
    await m.reply(f"💍 <b>{m.reply_to_message.from_user.first_name}</b>, тебе сделал предложение <b>{m.from_user.first_name}</b>! Согласишься?", reply_markup=kb.adjust(2).as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("ma_"))
async def marry_cb(c: types.CallbackQuery):
    _, act, tid, pid = c.data.split("_")
    if c.from_user.id != int(tid): return await c.answer("Не тебе предлагали! 😡", show_alert=True)
    p_name, _ = get_user_by_id(int(pid))
    if act == "y":
        conn = sqlite3.connect('loot.db'); cur = conn.cursor()
        cur.execute("UPDATE users SET partner_id = ? WHERE id = ?", (tid, pid)); cur.execute("UPDATE users SET partner_id = ? WHERE id = ?", (pid, tid))
        conn.commit(); conn.close()
        await c.message.edit_text(f"🥳 <b>ГОРЬКО!</b> 💍\n<b>{p_name}</b> и <b>{c.from_user.first_name}</b> теперь муж и жена!", parse_mode="HTML")
    else:
        await c.message.edit_text(f"💔 <b>{c.from_user.first_name}</b> отказал(а) в предложении. Сил тебе, {p_name}!", parse_mode="HTML")

@dp.message(Command("divorce"))
async def divorce(m: types.Message):
    u = get_user(m.from_user)
    if not u[5]: return await m.reply("Ты не в браке!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET partner_id = 0 WHERE id = ?", (m.from_user.id,)); cur.execute("UPDATE users SET partner_id = 0 WHERE id = ?", (u[5],))
    conn.commit(); conn.close()
    await m.reply("💔 Развод оформлен. Вы свободны!")

# --- ЭКОНОМИКА, БИЗНЕС И ПОДАРКИ ---
@dp.message(Command("loot"))
async def cmd_loot(m: types.Message):
    u = get_user(m.from_user); now = int(time.time())
    if now - u[1] < COOLDOWN_LOOT: return await m.reply("⏳ Рано еще! Подожди 10 минут!")
    win = random.randint(50, 200)
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp + ?, last_loot = ? WHERE id = ?", (win, now, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply(f"📦 Ты открыл кейс: <b>+{win}$</b>", parse_mode="HTML")

@dp.message(Command("business", "bussines"))
async def business(m: types.Message):
    u = get_user(m.from_user)
    gift_profit, _ = get_inventory_profit(m.from_user.id)
    gift_profit = min(400, gift_profit) # Лимит дохода от подарков
    
    await m.reply(f"🏢 <b>Бизнес и Акктивы</b>\n👥 Рабочих: {u[3]} (Доход: {u[3]*WORKER_PROFIT}$/ч)\n🎁 Прибыль с подарков: {gift_profit}$/ч\n\n💰 <b>Общий доход: {(u[3]*WORKER_PROFIT) + gift_profit}$/час</b>\n\n/hire - Нанять рабочего (1000$)\n/collect - Собрать прибыль", parse_mode="HTML")

@dp.message(Command("hire"))
async def hire(m: types.Message):
    u = get_user(m.from_user)
    if u[0] < WORKER_PRICE: return await m.reply("❌ Мало денег!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp - ?, workers = workers + 1 WHERE id = ?", (WORKER_PRICE, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply("👷 Рабочий нанят!")

@dp.message(Command("collect"))
async def collect(m: types.Message):
    u = get_user(m.from_user); now = int(time.time())
    hrs = (now - u[4]) // 3600
    if hrs < 1: return await m.reply("⏳ Копим минимум час!")
    
    gift_profit, _ = get_inventory_profit(m.from_user.id)
    gift_profit = min(400, gift_profit) # Ограничение дохода в 400$
    
    w_profit = hrs * u[3] * WORKER_PROFIT
    g_profit = hrs * gift_profit
    p = w_profit + g_profit
    
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("UPDATE users SET exp = exp + ?, last_collect = ? WHERE id = ?", (p, now, m.from_user.id))
    conn.commit(); conn.close()
    await m.reply(f"📥 Собрано: <b>{p}$</b>\n(От рабочих: {w_profit}$, От подарков: {g_profit}$)", parse_mode="HTML")

@dp.message(Command("pay"))
async def pay(m: types.Message, command: CommandObject):
    if not command.args or len(command.args.split()) < 2: return await m.reply("Пример: /pay @user 100")
    un = command.args.split()[0].replace('@', '').lower(); amt = int(command.args.split()[1])
    u = get_user(m.from_user)
    if u[0] < amt or amt <= 0: return await m.reply("❌ Ошибка суммы!")
    conn = sqlite3.connect('loot.db'); cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (un,))
    t = cur.fetchone()
    if not t: return await m.reply("Юзер не найден!")
    cur.execute("UPDATE users SET exp = exp - ? WHERE id = ?", (amt, m.from_user.id)); cur.execute("UPDATE users SET exp = exp + ? WHERE id = ?", (amt, t[0]))
    conn.commit(); conn.close()
    await m.reply(f"✅ Переведено {amt}$ для @{un}")

# --- СИСТЕМА ПОДАРКОВ ---
@dp.message(Command("gift"))
async def cmd_gift(m: types.Message, command: CommandObject):
    if not command.args:
        text = "🎁 <b>Магазин подарков:</b>\n\n"
        for k, v in GIFTS.items():
            text += f"<code>{k}</code>. {v['emoji']} <b>{v['name']}</b> — {v['price']}$ (Доход: {v['profit']}$/ч)\n"
        text += "\nИспользование:\nОтветом на сообщение: <code>/gift [ID]</code>\nПо юзернейму: <code>/gift @юзер [ID]</code>"
        return await m.reply(text, parse_mode="HTML")

    args = command.args.split(" ", 1)
    
    if m.reply_to_message:
        target_id = m.reply_to_message.from_user.id
        target_name = m.reply_to_message.from_user.first_name
        item_id = command.args.strip()
    else:
        if len(args) < 2 or not args[0].startswith("@"):
            return await m.reply("❌ Укажи @юзернейм и ID предмета, или используй команду ответом!")
        
        target_data = get_user_id_by_username(args[0])
        if not target_data: return await m.reply("❌ Пользователь не найден в БД!")
        target_id, target_name = target_data
        item_id = args[1].strip()

    if item_id not in GIFTS:
        return await m.reply("❌ Такого предмета нет! Введи /gift для списка.")
    if target_id == m.from_user.id:
        return await m.reply("❌ Нельзя дарить подарки самому себе!")

    gift = GIFTS[item_id]
    u = get_user(m.from_user)

    if u[0] < gift['price']:
        return await m.reply("❌ У тебя не хватает денег на этот подарок!")

    give_item(m.from_user.id, target_id, gift['price'], item_id)
    await m.reply(f"🎁 <b>{m.from_user.first_name}</b> подарил(а) <b>{target_name}</b> {gift['emoji']} {gift['name']}!", parse_mode="HTML")

@dp.message(Command("giftlove"))
async def cmd_giftlove(m: types.Message, command: CommandObject):
    u = get_user(m.from_user)
    if not u[5]: return await m.reply("❌ Ты не состоишь в браке!")
    
    if not command.args:
        return await m.reply("❌ Укажи ID подарка! Пример: <code>/giftlove 1</code>", parse_mode="HTML")
        
    item_id = command.args.strip()
    if item_id not in GIFTS:
        return await m.reply("❌ Такого предмета нет! Введи /gift для списка.")
        
    gift = GIFTS[item_id]
    if u[0] < gift['price']:
        return await m.reply("❌ У тебя не хватает денег на этот подарок!")
        
    partner_name, _ = get_user_by_id(u[5])
    give_item(m.from_user.id, u[5], gift['price'], item_id)
    
    await m.reply(f"💝 <b>{m.from_user.first_name}</b> подарил(а) своей половинке <b>{partner_name}</b> {gift['emoji']} {gift['name']}!", parse_mode="HTML")

# --- РПГ ДЕЙСТВИЯ ---
async def action(m, e, t_txt):
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else (m.text.split()[1] if len(m.text.split()) > 1 else "воздух")
    await m.reply(f"<b>{m.from_user.first_name}</b> {e} {t_txt} <b>{target}</b>", parse_mode="HTML")

# Команды (старые)
@dp.message(Command("hug"))
async def hug(m: types.Message): await action(m, "🫂", "обнял(а)")
@dp.message(Command("kiss"))
async def kiss(m: types.Message): await action(m, "💋", "поцеловал(а)")
@dp.message(Command("slap"))
async def slap(m: types.Message): await action(m, "👊", "дал(а) леща")
@dp.message(Command("fuck"))
async def fuck(m: types.Message): await action(m, "🔞", "оттрахал(а)")

# Новые текстовые РПГ триггеры (без слэша)
@dp.message(F.text.lower().in_({"поцеловать", "кусь", "оттрахать", "куни", "минет", "ласкать щеку"}))
async def text_rpg(m: types.Message):
    actions = {
        "поцеловать": ("💋", "поцеловал(а)"),
        "кусь": ("🦷", "сделал(а) кусь"),
        "оттрахать": ("🔞", "жестко оттрахал(а)"),
        "куни": ("👅", "сделал(а) куни"),
        "минет": ("🍌", "сделал(а) минет"),
        "ласкать щеку": ("🥰", "поласкал(а) щеку")
    }
    e, t_txt = actions[m.text.lower()]
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else "воздух"
    await m.reply(f"<b>{m.from_user.first_name}</b> {e} {t_txt} <b>{target}</b>", parse_mode="HTML")

@dp.message(F.text.lower() == "сделать комплимент")
async def send_compliment(m: types.Message):
    target = m.reply_to_message.from_user.first_name if m.reply_to_message else "себе"
    comp = random.choice(COMPLIMENTS)
    await m.reply(f"<b>{m.from_user.first_name}</b> делает комплимент <b>{target}</b>:\n\n<i>«{comp}»</i>", parse_mode="HTML")

# --- ТОП И РЕФ ---
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

# --- МИНЫ ---
g_m = {}
@dp.message(Command("min"))
async def mines(m: types.Message):
    f = [0]*21 + [1]*4; random.shuffle(f)
    g_m[m.from_user.id] = {"f": f, "s": 5, "w": 0, "o": []}
    kb = InlineKeyboardBuilder()
    for i in range(25): kb.button(text="❓", callback_data=f"mi_{i}")
    await m.reply("💣 <b>Минное поле</b> (5 ходов):", reply_markup=kb.adjust(5).as_markup(), parse_mode="HTML")

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
        await c.message.edit_text(f"🏁 Итог: <b>+{g['w']}$</b>", parse_mode="HTML"); del g_m[uid]

async def main():
    init_db()
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
