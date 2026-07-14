import logging
import random
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

BOT_TOKEN = "8898512215:AAFoNwPTyD0VhH9gOO2y3GVgAKIrvUxVsrI"
PAYMENT_LINK = "https://www.tinkoff.ru/rm/r_eRovAYeuEl.uJqDUNNlzS/zt6CM61150"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        purchased_50 INTEGER DEFAULT 0,
        purchased_100 INTEGER DEFAULT 0,
        purchased_150 INTEGER DEFAULT 0,
        purchased_200 INTEGER DEFAULT 0,
        referrer_id INTEGER,
        bonus INTEGER DEFAULT 0,
        bonus_paid INTEGER DEFAULT 0,
        bank_details TEXT DEFAULT '',
        reg_date TEXT,
        is_admin INTEGER DEFAULT 0
    )
""")
conn.commit()

PROMPTS_3 = [
    "киберпанк, неоновый дождь, фотореализм",
    "эльфийский лес, магия, утренний туман",
    "дракон в горах, эпическая фэнтези-атмосфера"
]
PROMPTS_5 = [
    "древний замок в грозу, магия, молнии, 8K",
    "кибер-самурай с катаной, неоновый город, ночь",
    "девушка-воин в доспехах, закат, реалистичные детали",
    "инопланетный лес со светящимися грибами, арт",
    "механический дракон, стимпанк, латунь и медь"
]
PROMPTS_7 = [
    "древний замок в грозу, магия, молнии, 8K",
    "кибер-самурай с катаной, неоновый город, ночь",
    "девушка-воин в доспехах, закат, реалистичные детали",
    "инопланетный лес со светящимися грибами, арт",
    "механический дракон, стимпанк, латунь и медь",
    "футуристический город, летающие машины, хай-тек",
    "портрет эльфийского короля, золото, эпический стиль"
]
PROMPTS_10 = [
    "древний замок в грозу, магия, молнии, 8K",
    "кибер-самурай с катаной, неоновый город, ночь",
    "девушка-воин в доспехах, закат, реалистичные детали",
    "инопланетный лес со светящимися грибами, арт",
    "механический дракон, стимпанк, латунь и медь",
    "футуристический город, летающие машины, хай-тек",
    "портрет эльфийского короля, золото, эпический стиль",
    "маг с посохом, звёздное небо, мистическая атмосфера",
    "подводный мир, кораллы и свет, акварельный стиль",
    "древний храм в джунглях, закат, таинственный свет"
]

def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def add_user(user_id, name, referrer_id=None):
    if not get_user(user_id):
        cursor.execute("INSERT INTO users (user_id, name, referrer_id, reg_date) VALUES (?, ?, ?, ?)",
                       (user_id, name, referrer_id, datetime.now().isoformat()))
        conn.commit()

def set_purchased(user_id, level):
    if level == 50:
        cursor.execute("UPDATE users SET purchased_50 = 1 WHERE user_id = ?", (user_id,))
    elif level == 100:
        cursor.execute("UPDATE users SET purchased_100 = 1 WHERE user_id = ?", (user_id,))
    elif level == 150:
        cursor.execute("UPDATE users SET purchased_150 = 1 WHERE user_id = ?", (user_id,))
    elif level == 200:
        cursor.execute("UPDATE users SET purchased_200 = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def get_purchased(user_id):
    user = get_user(user_id)
    if user:
        return user[2], user[3], user[4], user[5]
    return 0, 0, 0, 0

def add_bonus(user_id, amount):
    cursor.execute("UPDATE users SET bonus = bonus + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def mark_bonus_paid(user_id):
    cursor.execute("UPDATE users SET bonus = 0, bonus_paid = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def set_bank_details(user_id, details):
    cursor.execute("UPDATE users SET bank_details = ? WHERE user_id = ?", (details, user_id))
    conn.commit()

def get_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE purchased_100 = 1 OR purchased_150 = 1 OR purchased_200 = 1")
    total_purchased = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(bonus) FROM users")
    total_bonus = cursor.fetchone()[0] or 0
    return total_users, total_purchased, total_bonus

def get_referrals():
    cursor.execute("""
        SELECT u1.user_id, u1.name, u2.user_id, u2.name, u1.bonus, u1.bonus_paid, u1.bank_details
        FROM users u1
        JOIN users u2 ON u1.referrer_id = u2.user_id
        WHERE (u1.purchased_100 = 1 OR u1.purchased_150 = 1 OR u1.purchased_200 = 1)
        AND (u1.bonus > 0 OR u1.bonus_paid = 1)
    """)
    return cursor.fetchall()

def get_admin():
    cursor.execute("SELECT user_id FROM users WHERE is_admin = 1")
    result = cursor.fetchone()
    return result[0] if result else None

def set_admin(user_id):
    cursor.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def is_admin(user_id):
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

def get_main_keyboard(user_id):
    keyboard = [
        ["🎨 Сгенерировать картинку", "💎 Купить доступ"],
        ["👥 Реферальная ссылка", "🧹 Очистить чат"]
    ]
    if is_admin(user_id):
        keyboard.append(["⚙️ Админ-панель"])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context):
    user = update.effective_user
    first_name = user.first_name or "друг"
    user_id = user.id
    ref_id = None
    if context.args and context.args[0].startswith("ref_"):
        try:
            ref_id = int(context.args[0].split("_")[1])
        except:
            pass
    add_user(user_id, first_name, ref_id)
    await update.message.reply_text(
        f"🤖 Привет, {first_name}!\n"
        "Я генерирую промпты для нейросетей.\n\n"
        "🎨 Нажми «Сгенерировать картинку» — получишь 3 бесплатных промпта.\n"
        "💎 Купи доступ:\n"
        "   • 50 ₽ → 3 промпта\n"
        "   • 100 ₽ → 5 промптов\n"
        "   • 150 ₽ → 7 промптов\n"
        "   • 200 ₽ → 10 промптов\n\n"
        "👥 Приведи друга — он оплачивает тариф 100, 150 или 200 ₽, а ты получаешь 100 ₽ бонуса!\n"
        "Оплата по ссылке — быстро и безопасно.",
        reply_markup=get_main_keyboard(user_id)
    )

async def handle_text(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text
    if text == "🎨 Сгенерировать картинку":
        await generate_prompts(update, context)
    elif text == "💎 Купить доступ":
        await buy_menu(update, context)
    elif text == "👥 Реферальная ссылка":
        await referral_link(update, context)
    elif text == "🧹 Очистить чат":
        await clear_chat(update, context)
    elif text == "⚙️ Админ-панель" and is_admin(user_id):
        await admin_panel(update, context)
    else:
        await update.message.reply_text("❌ Неизвестная команда.", reply_markup=get_main_keyboard(user_id))

async def clear_chat(update: Update, context):
    user_id = update.effective_user.id
    for i in range(10):
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=update.message.message_id - i)
        except:
            pass
    await update.message.reply_text("🧹 Чат очищен!", reply_markup=get_main_keyboard(user_id))

async def generate_prompts(update: Update, context):
    user_id = update.effective_user.id
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        count = int(query.data.split("_")[1])
        if count == 5:
            prompts = PROMPTS_5
        elif count == 7:
            prompts = PROMPTS_7
        elif count == 10:
            prompts = PROMPTS_10
        elif count == 15:
            prompts = PROMPTS_10 * 2
        elif count == 20:
            prompts = PROMPTS_10 * 2 + PROMPTS_5
        else:
            prompts = PROMPTS_3
        picked = random.sample(prompts, min(count, len(prompts)))
        text = "🎨 Твои промпты:\n\n" + "\n".join(f"• {p}" for p in picked)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")]]))
        return
    picked = random.sample(PROMPTS_3, 3)
    text = "🎨 Твои бесплатные промпты:\n\n" + "\n".join(f"• {p}" for p in picked)
    await update.message.reply_text(text + "\n\n🔥 Хочешь больше? Купи доступ!", reply_markup=get_main_keyboard(user_id))

async def buy_menu(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("50 ₽ — 3 промпта", callback_data="buy_50")],
        [InlineKeyboardButton("100 ₽ — 5 промптов", callback_data="buy_100")],
        [InlineKeyboardButton("150 ₽ — 7 промптов", callback_data="buy_150")],
        [InlineKeyboardButton("200 ₽ — 10 промптов", callback_data="buy_200")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")],
    ]
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("💎 Выбери тариф:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text("💎 Выбери тариф:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_prompts(update: Update, context, price, count, level):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    purchased_50, purchased_100, purchased_150, purchased_200 = get_purchased(user_id)
    if (level == 50 and purchased_50) or (level == 100 and purchased_100) or (level == 150 and purchased_150) or (level == 200 and purchased_200):
        await query.edit_message_text("✅ У тебя уже есть этот тариф!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="buy_menu")]]))
        return
    keyboard = [
        [InlineKeyboardButton(f"💳 Оплатить {price} ₽ по ссылке", url=PAYMENT_LINK)],
        [InlineKeyboardButton("🔙 Назад", callback_data="buy_menu")],
    ]
    await query.edit_message_text(
        f"💎 Ты выбрал тариф {price} ₽ — {count} промптов.\n\n"
        "1️⃣ Нажми «Оплатить по ссылке»\n"
        "2️⃣ Переведи нужную сумму\n"
        "3️⃣ После оплаты напиши команду /confirm\n\n"
        "⚠️ Промпты могут задерживаться до 30 минут из-за ручной проверки.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buy_50(update: Update, context):
    await buy_prompts(update, context, 50, 3, 50)

async def buy_100(update: Update, context):
    await buy_prompts(update, context, 100, 5, 100)

async def buy_150(update: Update, context):
    await buy_prompts(update, context, 150, 7, 150)

async def buy_200(update: Update, context):
    await buy_prompts(update, context, 200, 10, 200)

async def confirm_payment(update: Update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ У тебя нет прав.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("❗ Используй: /confirm [сумма] [user_id]")
        return
    try:
        level = int(args[0])
        target_user = int(args[1]) if len(args) > 1 else user_id
    except:
        await update.message.reply_text("❌ Неверный формат. Используй: /confirm 100 123456789")
        return
    if level not in [50, 100, 150, 200]:
        await update.message.reply_text("❌ Доступны только тарифы: 50, 100, 150, 200")
        return
    set_purchased(target_user, level)
    if level in [100, 150, 200]:
        user = get_user(target_user)
        if user and user[5]:
            add_bonus(user[5], 100)
            await context.bot.send_message(user[5], "🎉 Твой друг оплатил тариф! Ты получил 100 ₽ бонуса. Добавь реквизиты в меню.")
    if level == 50:
        count = 3
        prompts = PROMPTS_3
    elif level == 100:
        count = 5
        prompts = PROMPTS_5
    elif level == 150:
        count = 7
        prompts = PROMPTS_7
    else:
        count = 10
        prompts = PROMPTS_10
    picked = random.sample(prompts, count)
    text = f"✅ Доступ к тарифу {level} ₽ открыт!\n\n" + "\n".join(f"• {p}" for p in picked)
    try:
        await context.bot.send_message(target_user, text + "\n\n🔥 Теперь ты можешь запрашивать новые промпты командой /more")
        await update.message.reply_text(f"✅ Доступ для пользователя {target_user} открыт.")
    except:
        await update.message.reply_text("❌ Не удалось отправить сообщение пользователю.")

async def more_prompts(update: Update, context):
    user_id = update.effective_user.id
    purchased_50, purchased_100, purchased_150, purchased_200 = get_purchased(user_id)
    if not (purchased_50 or purchased_100 or purchased_150 or purchased_200):
        await update.message.reply_text("❌ У тебя нет доступа. Купи тариф через /start")
        return
    if purchased_200:
        count = 10
        prompts = PROMPTS_10
    elif purchased_150:
        count = 7
        prompts = PROMPTS_7
    elif purchased_100:
        count = 5
        prompts = PROMPTS_5
    else:
        count = 3
        prompts = PROMPTS_3
    picked = random.sample(prompts, count)
    text = "🔥 Свежие промпты:\n\n" + "\n".join(f"• {p}" for p in picked)
    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

async def referral_link(update: Update, context):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    keyboard = [
        [InlineKeyboardButton("📋 Скопировать ссылку", url=link)],
        [InlineKeyboardButton("💰 Добавить реквизиты", callback_data="add_bank")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")],
    ]
    text = (
        f"👥 Твоя реферальная ссылка:\n{link}\n\n"
        "📌 ИНСТРУКЦИЯ:\n"
        "1. Отправь ссылку другу.\n"
        "2. Друг оплачивает тариф 100, 150 или 200 ₽.\n"
        "3. После оплаты он пишет /confirm.\n"
        "4. Ты получаешь 100 ₽ бонуса.\n"
        "5. Добавь реквизиты для выплаты.\n\n"
        "⚠️ Бонус НЕ начисляется за тариф 50 ₽!"
    )
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def add_bank_details(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📝 Введи свои реквизиты (номер карты или телефон):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="ref")]])
    )
    context.user_data['awaiting_bank'] = True

async def handle_bank_details(update: Update, context):
    if not context.user_data.get('awaiting_bank'):
        return
    user_id = update.effective_user.id
    set_bank_details(user_id, update.message.text)
    context.user_data['awaiting_bank'] = False
    await update.message.reply_text("✅ Реквизиты сохранены!", reply_markup=get_main_keyboard(user_id))

async def back_to_menu(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await query.edit_message_text("🔙 Возвращаю в главное меню.")
    await update.effective_user.send_message("Выбери действие:", reply_markup=get_main_keyboard(user_id))

async def admin_panel(update: Update, context):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    total_users, total_purchased, total_bonus = get_stats()
    text = (
        "⚙️ Админ-панель\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"✅ Купили тариф 100, 150 или 200 ₽: {total_purchased}\n"
        f"💰 Общий бонус к выплате: {total_bonus} ₽"
    )
    keyboard = [
        [InlineKeyboardButton("📊 Обновить статистику", callback_data="admin")],
        [InlineKeyboardButton("🎨 Бесплатные промпты (админ)", callback_data="admin_free")],
        [InlineKeyboardButton("👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton("📝 Список покупателей", callback_data="buyers")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="menu")],
    ]
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_free_prompts(update: Update, context):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("5 промптов", callback_data="free_5")],
        [InlineKeyboardButton("7 промптов", callback_data="free_7")],
        [InlineKeyboardButton("10 промптов", callback_data="free_10")],
        [InlineKeyboardButton("15 промптов", callback_data="free_15")],
        [InlineKeyboardButton("20 промптов", callback_data="free_20")],
        [InlineKeyboardButton("🔙 Назад", callback_data="admin")],
    ]
    await query.edit_message_text("🎨 Выбери количество промптов (бесплатно для админа):", reply_markup=InlineKeyboardMarkup(keyboard))

async def referrals_list(update: Update, context):
    query = update.callback_query
    await query.answer()
    referrals = get_referrals()
    if not referrals:
        await query.edit_message_text("📭 Пока нет рефералов.")
        return
    text = "👥 Рефералы:\n\n"
    keyboard = []
    for ref in referrals:
        user_id, name, referrer_id, referrer_name, bonus, paid, bank = ref
        status = "✅ Выплачено" if paid else f"💰 {bonus} ₽ (не выплачено)"
        bank_info = f"🏦 Реквизиты: {bank}" if bank else "❌ Реквизиты не добавлены"
        text += f"• {name} привёл {referrer_name}\n   {status}\n   {bank_info}\n\n"
        if not paid:
            keyboard.append([InlineKeyboardButton(f"✅ Выплачено {name}", callback_data=f"pay_{user_id}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def pay_bonus(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split("_")[1])
    mark_bonus_paid(user_id)
    try:
        await context.bot.send_message(user_id, "🎉 Твой бонус 100 ₽ выплачен! Спасибо!")
    except:
        pass
    await query.edit_message_text("✅ Бонус отмечен как выплаченный.")
    await referrals_list(update, context)

async def buyers_list(update: Update, context):
    query = update.callback_query
    await query.answer()
    cursor.execute("SELECT name, reg_date FROM users WHERE purchased_100 = 1 OR purchased_150 = 1 OR purchased_200 = 1")
    buyers = cursor.fetchall()
    if not buyers:
        await query.edit_message_text("📭 Пока нет покупателей.")
        return
    text = "📝 Список покупателей (100, 150, 200 ₽):\n\n" + "\n".join(f"• {b[0]} — {b[1]}" for b in buyers)
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def set_admin_command(update: Update, context):
    user_id = update.effective_user.id
    existing_admin = get_admin()
    if existing_admin:
        await update.message.reply_text("⛔ Администратор уже назначен. Доступ запрещён.")
        return
    set_admin(user_id)
    await update.message.reply_text(
        "✅ Ты назначен администратором!\n\n"
        "Теперь у тебя есть доступ к админ-панели.\n"
        "Ты можешь:\n"
        "• Смотреть статистику\n"
        "• Получать промпты бесплатно (5, 7, 10, 15, 20 шт)\n"
        "• Управлять рефералами и выплатами\n"
        "• Открывать доступ пользователям по /confirm"
    )

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("more", more_prompts))
    app.add_handler(CommandHandler("confirm", confirm_payment))
    app.add_handler(CommandHandler("setadmin", set_admin_command))
    app.add_handler(CallbackQueryHandler(generate_prompts, pattern="free_"))
    app.add_handler(CallbackQueryHandler(buy_menu, pattern="buy_menu"))
    app.add_handler(CallbackQueryHandler(buy_50, pattern="buy_50"))
    app.add_handler(CallbackQueryHandler(buy_100, pattern="buy_100"))
    app.add_handler(CallbackQueryHandler(buy_150, pattern="buy_150"))
    app.add_handler(CallbackQueryHandler(buy_200, pattern="buy_200"))
    app.add_handler(CallbackQueryHandler(referral_link, pattern="ref"))
    app.add_handler(CallbackQueryHandler(add_bank_details, pattern="add_bank"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="menu"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="admin"))
    app.add_handler(CallbackQueryHandler(admin_free_prompts, pattern="admin_free"))
    app.add_handler(CallbackQueryHandler(referrals_list, pattern="referrals"))
    app.add_handler(CallbackQueryHandler(pay_bonus, pattern="pay_"))
    app.add_handler(CallbackQueryHandler(buyers_list, pattern="buyers"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bank_details))

    print("✅ Бот запущен! Тарифы: 50, 100, 150, 200 ₽. Бонус за 100, 150, 200 ₽.")
    app.run_polling(allowed_updates=["message", "callback_query"])
