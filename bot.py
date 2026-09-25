import telebot, requests, base64, sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from telebot import types

BOT_TOKEN = '8999965807:AAGpkUtbhMevCGjkKAd6GNWyTIKk8R4LRRU'
API_KEY = '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'
CH = '@chadgpt_channel'
CH_LINK = 'https://t.me/chadgpt_channel'
ADMIN = 'tozose'

bot = telebot.TeleBot(BOT_TOKEN)
conn = sqlite3.connect('users.db', check_same_thread=False)
conn.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, premium_until TIMESTAMP, is_forever INTEGER DEFAULT 0, balance INTEGER DEFAULT 0, requests_today INTEGER DEFAULT 0, last_request_date TEXT, referrer_id INTEGER, referral_count INTEGER DEFAULT 0, is_admin INTEGER DEFAULT 0, extra_requests INTEGER DEFAULT 0)')
conn.commit()

BANNED = ["бомб","взрывчат","тротил","гексоген","оруж","пистолет","автомат","гранат","яд","отрав","токсин","наркотик","мефедрон","кокаин","героин","чит","взлом","хак","античит","вх","wallhack","aimbot","аимбот","esp","детск","цп","порно","теракт","убийств","киллер","карт","скам","фишинг","обнал","дроп"]
PHOTO_TRIG = ['нарисуй','сгенерируй','draw','generate','йото','нарис','сгенер','picture','image']

def banned(t): return any(w in t.lower() for w in BANNED)
def photo_req(t): return any(w in t.lower() for w in PHOTO_TRIG)

def is_admin(uid):
    r = conn.execute("SELECT is_admin, username FROM users WHERE user_id=?", (uid,)).fetchone()
    return r and (r[0] == 1 or (r[1] and r[1].lower() == ADMIN.lower()))

def sub(uid):
    try: return bot.get_chat_member(CH, uid).status in ['member','administrator','creator']
    except: return False

def reg(uid, un, ref=None):
    if conn.execute("SELECT user_id FROM users WHERE user_id=?", (uid,)).fetchone() is None:
        conn.execute("INSERT INTO users (user_id, username, referrer_id) VALUES (?, ?, ?)", (uid, un, ref))
        conn.commit()
        if ref and ref != uid:
            conn.execute("UPDATE users SET balance = balance + 10, referral_count = referral_count + 1 WHERE user_id=?", (ref,))
            conn.commit()

def limit(uid):
    if is_admin(uid): return True, 999
    r = conn.execute("SELECT premium_until, is_forever, requests_today, last_request_date, extra_requests FROM users WHERE user_id=?", (uid,)).fetchone()
    if not r: return True, 0
    pu, fv, rt, ld, ex = r
    today = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
    if fv: return True, 999
    if pu and datetime.fromisoformat(pu) > datetime.now(): return True, 999
    if ld != today:
        conn.execute("UPDATE users SET requests_today=0, last_request_date=? WHERE user_id=?", (today, uid))
        conn.commit()
        rt = 0
    lim = 10 + (ex or 0)
    return (True, rt) if rt < lim else (False, lim)

def inc(uid):
    if is_admin(uid): return
    today = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
    conn.execute("UPDATE users SET requests_today = requests_today + 1, last_request_date=? WHERE user_id=?", (today, uid))
    conn.commit()

def menu(uid):
    k = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    k.add("👤 Профиль", "🔗 Реф-ссылка", "💎 Купить премиум", "📢 Канал")
    if is_admin(uid): k.add("🛠 Админ-панель")
    return k

def sub_kb():
    k = types.InlineKeyboardMarkup()
    k.add(types.InlineKeyboardButton("📢 Подписаться", url=CH_LINK), types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
    return k

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.chat.id
    un = m.from_user.username or m.from_user.first_name
    args = m.text.split()
    ref = int(args[1].replace('ref_', '')) if len(args) > 1 and args[1].startswith('ref_') else None
    reg(uid, un, ref)
    if not sub(uid):
        bot.reply_to(m, "Подпишись на канал:", reply_markup=sub_kb()); return
    bot.reply_to(m, f"Привет, {m.from_user.first_name}! Я ChadGPT.", reply_markup=menu(uid))

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check_cb(c):
    if sub(c.from_user.id):
        bot.edit_message_text("✅ Подписка подтверждена!", c.message.chat.id, c.message.message_id)
        bot.send_message(c.message.chat.id, "Меню:", reply_markup=menu(c.from_user.id))
    else: bot.answer_callback_query(c.id, "❌ Не подписан!")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def prof(m):
    uid = m.chat.id
    r = conn.execute("SELECT balance, referral_count, premium_until, is_forever, requests_today, extra_requests FROM users WHERE user_id=?", (uid,)).fetchone()
    if r:
        b, rc, pu, fv, rt, ex = r
        st = "👑 АДМИН" if is_admin(uid) else ("👑 Навсегда" if fv else (f"⭐ до {pu[:10]}" if pu and datetime.fromisoformat(pu) > datetime.now() else "🆓 Бесплатно"))
        lim = 10 + (ex or 0)
        bot.reply_to(m, f"👤 Профиль\n\n🆔 ID: `{uid}`\n💰 Баланс: {b}₽\n👥 Друзей: {rc}\n📊 Запросов: {rt}/{lim}\n💎 Статус: {st}", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔗 Реф-ссылка")
def ref(m):
    uid = m.chat.id
    link = f"https://t.me/{bot.get_me().username}?start=ref_{uid}"
    r = conn.execute("SELECT balance, referral_count FROM users WHERE user_id=?", (uid,)).fetchone()
    b = r[0] if r else 0; rc = r[1] if r else 0
    bot.reply_to(m, f"🔗 {link}\n\n💰 {b}₽\n👥 Друзей: {rc}")

@bot.message_handler(func=lambda m: m.text == "📢 Канал")
def chan(m): bot.reply_to(m, f"📢 {CH_LINK}")

@bot.message_handler(func=lambda m: m.text == "💎 Купить премиум")
def buy(m):
    k = types.InlineKeyboardMarkup()
    for d, p in [("15",25),("30",45),("60",75),("90",100),("forever",200)]:
        k.add(types.InlineKeyboardButton(f"{d} — {p}⭐", callback_data=f"buy_{d}"))
    bot.reply_to(m, "Тариф:", reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def pb(c):
    d = c.data.replace('buy_', '')
    p = {'15':25,'30':45,'60':75,'90':100,'forever':200}
    bot.send_invoice(c.message.chat.id, title=f"Premium {d}", description="ChadGPT", invoice_payload=f"premium_{d}", provider_token="", currency="XTR", prices=[types.LabeledPrice(label="Premium", amount=p.get(d))])

@bot.pre_checkout_query_handler(func=lambda q: True)
def co(q): bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def gp(m):
    d = m.successful_payment.invoice_payload.replace('premium_', '')
    uid = m.chat.id
    if d == 'forever': conn.execute("UPDATE users SET is_forever=1 WHERE user_id=?", (uid,))
    else:
        u = datetime.now() + timedelta(days=int(d))
        conn.execute("UPDATE users SET premium_until=? WHERE user_id=?", (u.isoformat(), uid))
    conn.commit()
    bot.reply_to(m, "✅ Premium activated!")

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def ap(m):
    if not is_admin(m.chat.id): return
    k = types.InlineKeyboardMarkup()
    for t, c in [("📊 Статистика","astat"),("🎁 Выдать премиум","agive"),("❌ Забрать премиум","atake"),("➕ Выдать запросы","areq"),("👑 Выдать админку","amake"),("🚫 Забрать админку","aremove")]:
        k.add(types.InlineKeyboardButton(t, callback_data=c))
    bot.reply_to(m, "🛠 Админ-панель:", reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data == "astat")
def astat(c):
    if not is_admin(c.from_user.id): return
    t = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    p = conn.execute("SELECT COUNT(*) FROM users WHERE is_forever=1 OR premium_until > ?", (datetime.now().isoformat(),)).fetchone()[0]
    bot.edit_message_text(f"📊 Всего: {t}\n💎 Премиум: {p}", c.message.chat.id, c.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data in ["agive","atake","areq","amake","aremove"])
def adm(c):
    if not is_admin(c.from_user.id): return
    prompts = {"agive":"ID и дни: `123 30` (0=навсегда)","atake":"ID пользователя:","areq":"ID и сколько запросов: `123 50`","amake":"ID пользователя:","aremove":"ID пользователя:"}
    bot.edit_message_text(prompts[c.data], c.message.chat.id, c.message.message_id, parse_mode='Markdown')
    bot.register_next_step_handler(c.message, adm_next, c.data)

def adm_next(m, action):
    if not is_admin(m.chat.id): return
    try:
        if action == "agive":
            a = m.text.split(); tid = int(a[0]); d = int(a[1])
            if d == 0: conn.execute("UPDATE users SET is_forever=1 WHERE user_id=?", (tid,))
            else:
                u = datetime.now() + timedelta(days=d)
                conn.execute("UPDATE users SET premium_until=? WHERE user_id=?", (u.isoformat(), tid))
            msg = f"✅ Выдал премиум {tid} на {d} дней"
        elif action == "atake":
            tid = int(m.text.strip())
            conn.execute("UPDATE users SET premium_until=NULL, is_forever=0 WHERE user_id=?", (tid,))
            msg = f"✅ Забрал премиум у {tid}"
        elif action == "areq":
            a = m.text.split(); tid = int(a[0]); ex = int(a[1])
            conn.execute("UPDATE users SET extra_requests = extra_requests + ? WHERE user_id=?", (ex, tid))
            msg = f"✅ Выдал {ex} запросов {tid}"
        elif action == "amake":
            tid = int(m.text.strip())
            conn.execute("UPDATE users SET is_admin=1 WHERE user_id=?", (tid,))
            msg = f"✅ {tid} теперь админ"
        else:
            tid = int(m.text.strip())
            conn.execute("UPDATE users SET is_admin=0 WHERE user_id=?", (tid,))
            msg = f"✅ Забрал админку у {tid}"
        conn.commit()
        bot.reply_to(m, msg)
    except Exception as e:
        bot.reply_to(m, f"Ошибка: {e}")

@bot.message_handler(content_types=['photo'])
def hphoto(m):
    uid = m.chat.id
    if not sub(uid): bot.reply_to(m, "Подпишись на канал:", reply_markup=sub_kb()); return
    ok, used = limit(uid)
    if not ok: bot.reply_to(m, f"❌ Лимит {used} запросов/день. Купи премиум."); return
    try:
        p = m.photo[-1]
        d = bot.download_file(bot.get_file(p.file_id).file_path)
        b64 = base64.b64encode(d).decode('utf-8')
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json={"model": "qwen/qwen3.8-27b", "messages": [{"role": "user", "content": [{"type": "text", "text": "Реши задание. Объясни пошагово на русском, коротко."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}], "max_tokens": 1000}, timeout=60)
        dt = r.json()
        if 'choices' in dt:
            ans = dt['choices'][0]['message']['content']
            inc(uid)
            bot.reply_to(m, ans[:4000])
        else: bot.reply_to(m, f"Ошибка: {dt}")
    except Exception as e: bot.reply_to(m, f"Ошибка: {e}")

@bot.message_handler(func=lambda m: True)
def ai(m):
    uid = m.chat.id
    if not sub(uid): bot.reply_to(m, "Подпишись на канал:", reply_markup=sub_kb()); return
    if banned(m.text): bot.reply_to(m, "Бро, я такое не делаю."); return
    if photo_req(m.text): bot.reply_to(m, "Генерацию фото пока не умею, разраб скоро добавит! А решать по фото — могу, кидай."); return
    ok, used = limit(uid)
    if not ok: bot.reply_to(m, f"❌ Лимит {used} запросов/день. Купи премиум."); return
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json={"model": "openai/gpt-oss-120b", "messages": [{"role": "user", "content": m.text}]}, timeout=30)
        dt = r.json()
        if 'choices' in dt:
            ans = dt['choices'][0]['message']['content']
            inc(uid)
            bot.reply_to(m, ans)
        else: bot.reply_to(m, f"Ошибка: {dt}")
    except Exception as e: bot.reply_to(m, f"Ошибка: {e}")

print("ChadGPT запущен...")
bot.polling(none_stop=True)
