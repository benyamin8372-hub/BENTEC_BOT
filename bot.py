from telegram.ext import Application, CommandHandler
import random
import requests
from datetime import datetime

BOT_TOKEN = "8235193031:AAG_n49JcOlaeQtZpxTraSW5A3Q-EzvZ4GI"
WEATHER_API_KEY = "4118aca8b15bdab4efcccf2fae8bbddd"
NEWS_API_KEY = "bd1461abe9c441cb877da45947769db9"

async def start(update, context):
    await update.message.reply_text(
        "🎯 BENTEC با API های واقعی!\n\n"
        "💰 /currency - قیمت واقعی ارز\n"
        "🌤️ /weather - آب و هوای تهران\n"
        "📰 /news - اخبار داغ ایران\n"
        "🎮 /game - بازی\n"
        "😂 /joke - جوک\n"
        "🕐 /time - ساعت"
    )

async def currency(update, context):
    try:
        response = requests.get("https://api.tgju.org/v1/data/sana/json")
        data = response.json()
        usd = data["sana"]["data"]["price"]
        
        response_gold = requests.get("https://api.tgju.org/v1/data/geram18/json")
        gold_data = response_gold.json()
        gold = gold_data["geram18"]["data"]["price"]
        
        text = f"""🏦 قیمت‌های لحظه‌ای:

💰 دلار: {usd:,} تومان
🥇 طلا: {gold:,} تومان

📊 منبع: TGJU"""
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text("❌ خطا در دریافت قیمت")

async def weather(update, context):
    try:
        response = requests.get(f"http://api.openweathermap.org/data/2.5/weather?q=Tehran&appid={WEATHER_API_KEY}&units=metric&lang=fa")
        
        if response.status_code == 200:
            data = response.json()
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            feels_like = data["main"]["feels_like"]
            
            weather_text = f"""🌤️ آب و هوای تهران:

🌡️ دما: {temp}°C
💨 احساس: {feels_like}°C  
☁️ وضعیت: {desc}
💧 رطوبت: {humidity}%

✅ اطلاعات واقعی"""
            await update.message.reply_text(weather_text)
        else:
            await update.message.reply_text("❌ خطا در دریافت آب و هوا")
            
    except Exception as e:
        await update.message.reply_text("❌ خطا در اتصال")

async def news(update, context):
    try:
        response = requests.get(f"https://newsapi.org/v2/top-headlines?country=ir&apiKey={NEWS_API_KEY}")
        data = response.json()
        
        if data["articles"]:
            article = data["articles"][0]  # اولین خبر
            title = article["title"]
            source = article["source"]["name"]
            
            news_text = f"""📰 آخرین خبر ایران:

{title}

📡 منبع: {source}
⏰ اخبار لحظه‌ای"""
            await update.message.reply_text(news_text)
        else:
            await update.message.reply_text("📰 خبری یافت نشد")
            
    except Exception as e:
        await update.message.reply_text("❌ خطا در دریافت اخبار")

async def game(update, context):
    number = random.randint(1, 10)
    await update.message.reply_text(f"🎮 عدد بین ۱ تا ۱۰: {number}")

async def joke(update, context):
    jokes = [
        "BENTEC: حالا هم قیمت واقعی، هم آب و هوا، هم اخبار واقعی! 🚀",
        "کاربر: چه ربات کاملی!\nBENTEC: ممنون! API های واقعی دارم ✅",
        "دیگه نیازی به ۱۰ تا اپ مختلف نداری! BENTEC همه کاره است! 💪"
    ]
    await update.message.reply_text(random.choice(jokes))

async def time(update, context):
    now = datetime.now()
    await update.message.reply_text(f"🕐 {now.strftime('%H:%M - %Y/%m/%d')}")

# اجرای ربات
app = Application.builder().token(BOT_TOKEN).build()

commands = [
    ("start", start), ("currency", currency), ("weather", weather),
    ("news", news), ("game", game), ("joke", joke), ("time", time)
]

for cmd, handler in commands:
    app.add_handler(CommandHandler(cmd, handler))

print("🔥 BENTEC با تمام API های واقعی اجرا شد!")
app.run_polling()
