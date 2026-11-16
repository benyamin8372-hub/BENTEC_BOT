import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone
from urllib.parse import quote

import feedparser
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB_PATH = os.getenv("DB_PATH", "bentech.sqlite3")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bentech")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it as an environment secret.")

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT,
            city TEXT DEFAULT '', subscribed INTEGER DEFAULT 1, joined_at TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS sent_articles(
            url TEXT PRIMARY KEY, title TEXT, sent_at TEXT)""")

def register_user(user):
    with connect() as con:
        con.execute("""INSERT INTO users(user_id,first_name,username,joined_at)
            VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name, username=excluded.username""",
            (user.id, user.first_name or "", user.username or "", datetime.now(timezone.utc).isoformat()))

def set_subscription(user_id, enabled):
    with connect() as con:
        con.execute("UPDATE users SET subscribed=? WHERE user_id=?", (1 if enabled else 0, user_id))

def set_city(user_id, city):
    with connect() as con:
        con.execute("UPDATE users SET city=? WHERE user_id=?", (city, user_id))

def get_city(user_id):
    with connect() as con:
        row = con.execute("SELECT city FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["city"] if row else ""

def recipients():
    with connect() as con:
        return [r["user_id"] for r in con.execute("SELECT user_id FROM users WHERE subscribed=1").fetchall()]

def stats():
    with connect() as con:
        total = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = con.execute("SELECT COUNT(*) FROM users WHERE subscribed=1").fetchone()[0]
        return total, active

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📰 آخرین اخبار", callback_data="news"),
         InlineKeyboardButton("🌤 هواشناسی", callback_data="weather")],
        [InlineKeyboardButton("📍 تنظیم شهر", callback_data="setcity"),
         InlineKeyboardButton("🔔 عضویت خبرنامه", callback_data="subscribe")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
    ])

async def get_news(limit=5):
    url = "https://news.google.com/rss/search?q=" + quote("اخبار ایران OR اخبار جهان") + "&hl=fa&gl=IR&ceid=IR:fa"
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        response = await client.get(url, headers={"User-Agent": "BENTECH-NewsBot/1.0"})
        response.raise_for_status()
    feed = feedparser.parse(response.text)
    return [{
        "title": e.get("title", "بدون عنوان"),
        "url": e.get("link", ""),
        "source": e.get("source", {}).get("title", "منبع خبری")
    } for e in feed.entries[:limit] if e.get("link")]

def format_news(items, heading="📰 <b>آخرین خبرها</b>"):
    if not items:
        return "در حال حاضر خبر تازه‌ای دریافت نشد."
    lines = [heading, ""]
    for i, item in enumerate(items, 1):
        title = item["title"].replace("<", "&lt;").replace(">", "&gt;")
        source = item["source"].replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f'{i}. <a href="{item["url"]}">{title}</a>\n   <i>{source}</i>')
    return "\n\n".join(lines)

async def get_weather(city):
    async with httpx.AsyncClient(timeout=20) as client:
        geo = await client.get("https://geocoding-api.open-meteo.com/v1/search",
                               params={"name": city, "count": 1, "language": "fa", "format": "json"})
        geo.raise_for_status()
        places = geo.json().get("results") or []
        if not places:
            return None
        place = places[0]
        weather = await client.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": place["latitude"], "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min", "timezone": "auto"})
        weather.raise_for_status()
        data = weather.json()
    cur, daily = data.get("current", {}), data.get("daily", {})
    labels = {0:"صاف",1:"عمدتاً صاف",2:"نیمه‌ابری",3:"ابری",45:"مه‌آلود",48:"مه یخ‌زن",
              51:"نم‌نم باران",53:"باران ریز",55:"باران ریز شدید",61:"باران سبک",63:"باران",65:"باران شدید",
              71:"برف سبک",73:"برف",75:"برف شدید",80:"رگبار پراکنده",81:"رگبار",82:"رگبار شدید",
              95:"رعدوبرق",96:"رعدوبرق و تگرگ",99:"رعدوبرق و تگرگ شدید"}
    return (f"🌤 <b>آب‌وهوای {place.get('name', city)}، {place.get('country','')}</b>\n\n"
            f"🌡 دما: <b>{cur.get('temperature_2m','—')}°C</b>\n"
            f"🤔 دمای محسوس: {cur.get('apparent_temperature','—')}°C\n"
            f"☁️ وضعیت: {labels.get(cur.get('weather_code'), 'نامشخص')}\n"
            f"💧 رطوبت: {cur.get('relative_humidity_2m','—')}٪\n"
            f"💨 باد: {cur.get('wind_speed_10m','—')} km/h\n"
            f"⬆️ بیشینه: {daily.get('temperature_2m_max',['—'])[0]}°C | "
            f"⬇️ کمینه: {daily.get('temperature_2m_min',['—'])[0]}°C\n\n"
            "<i>منبع: Open-Meteo</i>")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)
    await update.effective_message.reply_text(
        f"سلام {update.effective_user.first_name or ''}!\nبه <b>BENTECH</b> خوش آمدی.\n"
        "خبرها و هواشناسی را از من دریافت کن. خبرهای تازه هر ساعت به‌صورت خودکار ارسال می‌شوند.",
        parse_mode=ParseMode.HTML, reply_markup=menu())

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.effective_message.reply_text(format_news(await get_news()), parse_mode=ParseMode.HTML,
                                                   disable_web_page_preview=True)
    except Exception:
        log.exception("news request failed")
        await update.effective_message.reply_text("دریافت خبرها ناموفق بود؛ کمی بعد دوباره تلاش کن.")

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = " ".join(context.args).strip() if context.args else get_city(update.effective_user.id)
    if not city:
        await update.effective_message.reply_text("نام شهر را وارد کن: /weather Berlin")
        return
    try:
        result = await get_weather(city)
        if result:
            set_city(update.effective_user.id, city)
            await update.effective_message.reply_text(result, parse_mode=ParseMode.HTML)
        else:
            await update.effective_message.reply_text("شهر پیدا نشد. نام دیگری امتحان کن.")
    except Exception:
        log.exception("weather request failed")
        await update.effective_message.reply_text("دریافت هواشناسی ناموفق بود.")

async def setcity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = " ".join(context.args).strip()
    if not city:
        await update.effective_message.reply_text("استفاده: /setcity Tehran")
        return
    set_city(update.effective_user.id, city)
    await update.effective_message.reply_text(f"شهر پیش‌فرض روی «{city}» ذخیره شد.")

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user)
    set_subscription(update.effective_user.id, True)
    await update.effective_message.reply_text("عضویت خبرنامه ساعتی فعال شد. برای توقف /unsubscribe را بزن.")

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_subscription(update.effective_user.id, False)
    await update.effective_message.reply_text("ارسال خودکار خبر برایت متوقف شد. هر زمان خواستی /subscribe را بزن.")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.effective_message.reply_text("⛔ دسترسی مجاز نیست.")
        return
    total, active = stats()
    await update.effective_message.reply_text(
        f"🛠 <b>پنل مدیریت BENTECH</b>\n👥 کل کاربران: {total}\n🔔 اعضای خبرنامه: {active}",
        parse_mode=ParseMode.HTML)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "news":
        await news_command(update, context)
    elif query.data == "weather":
        city = get_city(query.from_user.id)
        if city:
            result = await get_weather(city)
            await query.message.reply_text(result or "شهر ذخیره‌شده پیدا نشد.", parse_mode=ParseMode.HTML)
        else:
            await query.message.reply_text("ابتدا شهر را ذخیره کن: /setcity Berlin")
    elif query.data == "setcity":
        await query.message.reply_text("برای ذخیره شهر بنویس: /setcity Berlin")
    elif query.data == "subscribe":
        set_subscription(query.from_user.id, True)
        await query.message.reply_text("عضویت خبرنامه ساعتی فعال شد.")
    elif query.data == "help":
        await query.message.reply_text(
            "/news — خبرها\n/weather Berlin — هواشناسی\n/setcity Berlin — ذخیره شهر\n"
            "/subscribe — فعال‌سازی خبر ساعتی\n/unsubscribe — توقف خبر ساعتی\n/admin — پنل مدیریت")

async def hourly_broadcast(context: ContextTypes.DEFAULT_TYPE):
    try:
        items = await get_news(5)
        if not items:
            return
        # Only broadcast links not previously delivered, avoiding repeated headlines.
        with connect() as con:
            fresh = [item for item in items if not con.execute(
                "SELECT 1 FROM sent_articles WHERE url=?", (item["url"],)).fetchone()]
            if fresh:
                stamp = datetime.now(timezone.utc).isoformat()
                con.executemany("INSERT OR IGNORE INTO sent_articles(url,title,sent_at) VALUES(?,?,?)",
                                [(x["url"], x["title"], stamp) for x in fresh])
        if not fresh:
            log.info("Hourly news: no new stories.")
            return
        text = format_news(fresh, "⏰ <b>خبرنامه خودکار ساعتی BENTECH</b>")
        for uid in recipients():
            try:
                await context.bot.send_message(uid, text, parse_mode=ParseMode.HTML,
                                               disable_web_page_preview=True)
                await asyncio.sleep(0.05)
            except Exception as exc:
                log.warning("Broadcast to %s failed: %s", uid, exc)
    except Exception:
        log.exception("Hourly broadcast failed")

async def post_init(app: Application):
    init_db()
    # First broadcast is after one hour; then repeats every 3600 seconds.
    app.job_queue.run_repeating(hourly_broadcast, interval=3600, first=3600, name="hourly_news")

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("news", news_command))
    app.add_handler(CommandHandler("weather", weather_command))
    app.add_handler(CommandHandler("setcity", setcity_command))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    log.info("BENTECH is starting")
    app.run_polling()

if __name__ == "__main__":
    main()
