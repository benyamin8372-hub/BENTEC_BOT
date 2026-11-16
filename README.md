# BENTECH — ربات تلگرام خبر و هواشناسی

ربات فارسی تلگرام برای دریافت خبرهای فارسی و هواشناسی شهرهای مختلف.

## قابلیت‌ها
- دریافت آخرین تیترها از Google News RSS
- ارسال خودکار خبرهای جدید هر یک ساعت برای اعضای خبرنامه
- جلوگیری از ارسال مجدد لینک خبرهای قبلاً ارسال‌شده
- /subscribe و /unsubscribe برای مدیریت دریافت خبر ساعتی
- هواشناسی فعلی شهر با Open-Meteo
- ذخیره شهر پیش‌فرض هر کاربر
- پنل مدیر و شمارش کاربران

## راه‌اندازی محلی
1. Python 3.10 یا بالاتر نصب کن.
2. فایل `.env.example` را به `.env` تغییر نام بده.
3. `BOT_TOKEN` و `ADMIN_IDS` را در `.env` قرار بده.
4. اجرا:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```

## فرمان‌ها
- `/start` شروع
- `/news` خبرهای تازه
- `/weather Berlin` هواشناسی
- `/setcity Tehran` ذخیره شهر
- `/subscribe` فعال‌سازی خبر ساعتی
- `/unsubscribe` توقف خبر ساعتی
- `/admin` آمار مدیر

کاربران جدید به‌صورت پیش‌فرض عضو خبرنامه ساعتی می‌شوند. هر کاربر می‌تواند با `/unsubscribe` آن را متوقف کند.

## استقرار روی Render
1. مخزن را به Render متصل کن و یک **Background Worker** بساز.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `python main.py`
4. متغیرهای محیطی `BOT_TOKEN` و `ADMIN_IDS` را در داشبورد Render تنظیم کن.
5. برای حفظ SQLite، یک Persistent Disk در مسیر `/var/data` متصل کن و `DB_PATH=/var/data/bentech.sqlite3` قرار بده.

ربات باید به‌صورت worker همیشه‌روشن اجرا شود؛ صرفاً بارگذاری سورس در GitHub اجرای ۲۴ساعته را فعال نمی‌کند.

## منابع داده
- خبر: Google News RSS
- هواشناسی و مکان‌یابی: Open-Meteo

## امنیت
هیچ توکن یا کلید API را در کد یا GitHub قرار نده. از Environment Variables / Secrets استفاده کن.
