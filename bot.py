import json
import logging
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    CallbackQueryHandler, MessageHandler, ContextTypes, filters, AIORateLimiter
)

BOT_TOKEN = "8368966703:AAH6ITzlxfryVXPcLDRAHiSXHIeSixquToc"  # ← твой токен
DEFAULT_TZ = "Europe/Kyiv"
DEFAULT_TIME = "09:00"
USERS_FILE = Path("users.json")

AFFIRMATIONS = [
    "Я выбираю движение вперёд — спокойно, уверенно, умно.",
    "Мои решения точны, а действия приносят результат.",
    "Сегодня я создаю ценность и получаю больше, чем вчера.",
    "Я дисциплинирован(а), смела и добиваюсь своего.",
    "Мой разум ясен, энергия направлена, цели достижимы.",
    "Каждый шаг усиливает мою репутацию и капитал.",
    "Я действую стратегически и эффективно — без лишнего шума.",
    "Я учусь быстрее, работаю умнее и зарабатываю больше.",
    "Я люблю деньги, и деньги любят меня.",
    "Я отлично знаю, как мне заработать деньги.",
    "Я получаю от Вселенной все, что мне нужно.",
    "Мой доход с каждым днем увеличивается все больше и больше.",
    "Моя работа приносит пользу для моих клиентов.",
    "Я настроен(а) на частоту богатства Вселенной.",
    "Я во всем вижу возможности и ресурсы для привлечения денег",
    "Я притягиваю в свою жизнь талантливых, порядочных, трудолюбивых клиентов.",
    "У меня всегда есть огромное количество идей и ресурсов для получения денег.",
    "Я всегда имею столько денег, сколько мне нужно.",
    "Любые проблемы и неприятности я превращаю в деньги.",
    "Мои доходы увеличиваются с каждым днем.",
    "Я привлекаю богатство и изобилие из разных источников в виде разных валют, чеков, подарков, возможностей.",
    "Я привлекаю деньги и богатство с любовью и благодарностью.",
    "Я радуюсь большим и маленьким успехам.",
    "Я благодарю Вселенную за все, что она дает мне",
    "Я всегда получаю то, что мне нужно, вовремя и в достаточном количестве.",
    "Деньги дают мне свободу в реализации всех моих планов и желаний.",
    "Деньги меня любят. Я достоин больших денег.",
    "Я всегда достигаю того, чего хочу.",
    "Деньги приходят ко мне легко и с удовольствием.",
    "Чем больше денег я трачу, тем больше ко мне приходит.",
    "Я — магнит для денег и богатства.",
    "С каждым днем мои доходы растут.",
    "Я выбираю мысли, которые делают меня богаче и счастливее.",
    "Я действительно особенная.",
    "Я рождена, чтобы любить и быть любимой.",
    "Все мои свидания проходят незабываемо.",
    "Я достоин/достойна настоящей любви.",
    "Я заслуживаю любви.",
    "Я отпускаю свой страх любви.",
    "Я легко знакомлюсь с людьми.",
    "Я нравлюсь тем, кто нравится мне.",
    "Любовь тянется ко мне.",
    "Моя любовь приходит ко мне в самое подходящее время для нас обоих.",
    "Мой партнер ищет меня прямо сейчас, и мы находим друг друга.",
    "У Вселенной для меня заготовлено нечто прекрасное – такое, о чем я не мог(ла) и подумать.",
    "Я достойна безусловной любви и доброты.",
    "Я осознаю себе цену.",
    "Я достоин/достойна того, чтобы меня любили всем сердцем.",
    "Я позволяю любви войти в мою жизнь.",
]

def load_users():
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return {}

def save_users(data):
    USERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def stable_daily_index(chat_id: int, date_utc: datetime) -> int:
    seed = hash((chat_id, date_utc.date().toordinal()))
    return abs(seed) % len(AFFIRMATIONS)

def normalize_time_str(text: str) -> str | None:
    try:
        hh, mm = text.strip().split(":")
        h, m = int(hh), int(mm)
        if 0 <= h < 24 and 0 <= m < 60:
            return f"{h:02d}:{m:02d}"
    except Exception:
        pass
    return None

def keyboard_main(time_str: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Получить аффирмацию сейчас 🔮", callback_data="now")],
        [InlineKeyboardButton(f"Изменить время ⏰ ({time_str})", callback_data="change_time")],
    ])

async def send_today_affirmation(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE, force_random=False):
    if force_random:
        idx = abs(hash((chat_id, int(datetime.now(timezone.utc).timestamp())))) % len(AFFIRMATIONS)
    else:
        idx = stable_daily_index(chat_id, datetime.now(timezone.utc))
    text = AFFIRMATIONS[idx]
    await ctx.bot.send_message(chat_id, f"✨ <b>Аффирмация</b>\n\n{text}", parse_mode=ParseMode.HTML)

async def daily_job(ctx: ContextTypes.DEFAULT_TYPE):
    await send_today_affirmation(ctx.job.chat_id, ctx)

def schedule(app, chat_id: int, time_str: str, tz: str):
    for j in app.job_queue.get_jobs_by_name(f"daily_{chat_id}"):
        j.schedule_removal()
    hh, mm = map(int, time_str.split(":"))
    app.job_queue.run_daily(
        daily_job,
        time(hour=hh, minute=mm, tzinfo=ZoneInfo(tz)),
        days=(0,1,2,3,4,5,6),
        chat_id=chat_id,
        name=f"daily_{chat_id}",
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = load_users()
    user = data.get(str(chat_id)) or {"time": DEFAULT_TIME, "tz": DEFAULT_TZ}
    data[str(chat_id)] = user
    save_users(data)
    schedule(context.application, chat_id, user["time"], user["tz"])
    await update.message.reply_text(
        f"Привет! Я буду присылать аффирмации каждый день.\n"
        f"Текущее время: {user['time']} ({user['tz']}).\n"
        "Можно изменить: /settime HH:MM и /settz Europe/Kyiv",
        reply_markup=keyboard_main(user["time"])
    )

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_today_affirmation(update.effective_chat.id, context)

async def random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_today_affirmation(update.effective_chat.id, context, force_random=True)

async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Использование: /settime HH:MM")
        return
    t = normalize_time_str(context.args[0])
    if not t:
        await update.message.reply_text("Неверный формат. Пример: 09:00")
        return
    data = load_users()
    user = data.get(str(chat_id)) or {"time": DEFAULT_TIME, "tz": DEFAULT_TZ}
    user["time"] = t
    data[str(chat_id)] = user
    save_users(data)
    schedule(context.application, chat_id, user["time"], user["tz"])
    await update.message.reply_text(f"Готово! Теперь в {t} ({user['tz']}).")

async def settz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        await update.message.reply_text("Использование: /settz Europe/Kyiv")
        return
    tz = context.args[0]
    try:
        ZoneInfo(tz)
    except Exception:
        await update.message.reply_text("Неизвестная таймзона. Пример: Europe/Kyiv")
        return
    data = load_users()
    user = data.get(str(chat_id)) or {"time": DEFAULT_TIME, "tz": DEFAULT_TZ}
    user["tz"] = tz
    data[str(chat_id)] = user
    save_users(data)
    schedule(context.application, chat_id, user["time"], user["tz"])
    await update.message.reply_text(f"Таймзона изменена: {tz}")

async def buttons_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat.id
    if q.data == "now":
        await send_today_affirmation(chat_id, context)
    elif q.data == "change_time":
        await q.message.reply_text("Напиши: /settime HH:MM")

def main():
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN:
        raise RuntimeError("Нет BOT_TOKEN! Укажи токен.")
    app = ApplicationBuilder().token(BOT_TOKEN).rate_limiter(AIORateLimiter()).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today))
    app.add_handler(CommandHandler("random", random))
    app.add_handler(CommandHandler("settime", settime))
    app.add_handler(CommandHandler("settz", settz))
    app.add_handler(CallbackQueryHandler(buttons_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, today))
    data = load_users()
    for cid, u in data.items():
        try:
            schedule(app, int(cid), u.get("time", DEFAULT_TIME), u.get("tz", DEFAULT_TZ))
        except Exception:
            pass
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
