import os
import csv
import sqlite3
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# ============================================================
# تنظیمات
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

DB_FILE = "safety_culture_bot.db"
CSV_FILE = "safety_culture_responses.csv"

# اگر نمی‌خواهید گزینه «موردی ندارم» نمایش داده شود، False کنید.
ALLOW_NOT_APPLICABLE = True

OPTIONS = [
    ("کاملاً مخالفم", 1),
    ("مخالفم", 2),
    ("نظری ندارم", 3),
    ("موافقم", 4),
    ("کاملاً موافقم", 5),
]

if ALLOW_NOT_APPLICABLE:
    OPTIONS.append(("موردی ندارم", None))


# ============================================================
# پرسشنامه نهایی: 47 گویه در 8 بعد
# مبنا: بخش «نسخه نهایی پیشنهادی پرسشنامه» فایل ارسالی
# ============================================================

DIMENSIONS = [
    {
        "name": "تعهد و رهبری ایمنی",
        "questions": [
            "مدیریت ارشد سازمان در تصمیمگیریهای مدیریتی، الزامات ایمنی را بهطور مستمر مورد توجه و اولویت قرار میدهد.",
            "مدیریت سازمان منابع مالی و انسانی مورد نیاز برای اجرای مؤثر برنامههای ایمنی را تأمین میکند.",
            "مدیران و سرپرستان با رفتار عملی خود (نه فقط گفتار) الگوی رعایت ایمنی برای کارکنان هستند.",
            "مدیران در بررسی حوادث و رویدادهای ایمنی، مسئولیت خود و سازمان را در قبال عوامل مدیریتی مؤثر مورد توجه قرار میدهند.",
            "هنگام مشاهده رفتار ناایمن کارکنان، مدیران و سرپرستان بهصورت مناسب مداخله کرده و روش صحیح و ایمن انجام کار را آموزش میدهند.",
            "حتی در شرایط فشار تولید، مدیران و سرپرستان از کارکنان میخواهند الزامات ایمنی را رعایت کنند.",
        ],
    },
    {
        "name": "ارتباطات و گزارشدهی ایمنی",
        "questions": [
            "ارتباطات مربوط به مسائل ایمنی بین مدیریت، سرپرستان و کارکنان بهصورت منظم و دوسویه انجام میشود.",
            "کارکنان میتوانند بدون ترس از توبیخ شدن، مشکلات ایمنی را به مدیران گزارش کنند.",
            "فرآیند گزارشدهی نقصها و شرایط ناایمن، ساده و سریع است و به تشریفات یا کاغذبازی پیچیده نیاز ندارد.",
            "پیش از شروع هر شیفت کاری یا انجام فعالیتهای خاص و پرخطر، نکات ایمنی مرتبط به کارکنان منتقل میشود.",
            "پس از گزارش یک مشکل یا شرایط ناایمن، نتیجه بررسی و اقدامات انجامشده به گزارشدهنده اطلاع داده میشود.",
            "گزارشهای مربوط به مسائل ایمنی در سازمان بهطور جدی بررسی شده و برای رفع آنها اقدامات لازم انجام میشود.",
        ],
    },
    {
        "name": "آموزش، شایستگی و آگاهی ایمنی",
        "questions": [
            "آموزشهای ایمنی اولیه بدو استخدام برای همه کارکنان جدید بهطور کامل و متناسب اجرا میشود.",
            "دورههای بازآموزی ایمنی بهصورت منظم و با فاصله زمانی مناسب برگزار میشود.",
            "کارکنان شاغل در ایستگاههای کاری پرخطر آموزش تخصصی متناسب با آن ایستگاه دریافت کردهاند.",
            "پس از دورههای آموزشی، یادگیری و مهارت کارکنان بهطور عملی سنجیده میشود، نه صرفاً حضور در کلاس.",
            "شایستگی، مهارت و دانش کارکنان برای انجام ایمن وظایف شغلی، بهصورت دورهای ارزیابی میشود.",
            "کارکنان از خطرات ایمنی مرتبط با فعالیتهای شغلی خود آگاهی دارند.",
            "در صورت تغییر در فرایند، تجهیزات یا روشهای کاری، آموزشهای ایمنی متناسب با تغییرات ارائه میشود.",
        ],
    },
    {
        "name": "مشارکت و مسئولیتپذیری کارکنان در ایمنی",
        "questions": [
            "کارکنان بهطور فعال در کمیتههای ایمنی و جلسات شناسایی خطر مشارکت دارند.",
            "نظر کارکنان هنگام تدوین یا اصلاح دستورالعملها و رویههای ایمنی مورد توجه قرار میگیرد.",
            "کارکنان بهطور داوطلبانه پیشنهادهای بهبود ایمنی ارائه میدهند.",
            "پیشنهادهای ایمنی کارکنان بهطور جدی بررسی شده و پیشنهادهای قابل اجرا در اقدامات ایمنی مورد استفاده قرار میگیرند.",
            "کارکنان در صورت مشاهده یک خطر جدی و فوری، اختیار دارند فعالیت ناایمن را متوقف کرده و موضوع را گزارش کنند.",
            "کارکنان خود را در قبال رعایت الزامات ایمنی در انجام وظایف شغلی مسئول میدانند.",
        ],
    },
    {
        "name": "مدیریت ریسک",
        "questions": [
            "قبل از شروع هر کار، خطرات ایمنی مرتبط با فعالیتها و فرایندهای کاری بهصورت منظم شناسایی میشوند.",
            "در شناسایی خطرات، علاوه بر حوادث رخداده، شرایط و فعالیتهایی که میتوانند منجر به حادثه شوند نیز مورد توجه قرار میگیرند.",
            "خطرات اختصاصی خطوط تولید خودرو (مانند کار با رباتهای جوشکاری، پرسهای بدنهسازی و مواد شیمیایی در خط رنگ) بهطور مشخص در فرایند شناسایی خطرات مورد توجه قرار میگیرند.",
            "ریسکهای ایمنی شناساییشده بر اساس میزان احتمال وقوع و شدت پیامدهای آنها ارزیابی میشوند.",
            "برای ریسکهای شناساییشده، اقدامات کنترلی متناسب با سطح ریسک اجرا میشود.",
            "پس از ایجاد تغییر در تجهیزات، فرایندها یا مواد مورد استفاده، خطرات و ریسکهای ایمنی مجددًا ارزیابی میشوند.",
            "پس از وقوع حادثه یا شبهحادثه، ارزیابی ریسک مربوط به فعالیت یا فرایند مورد نظر بازنگری میشود.",
        ],
    },
    {
        "name": "ارزش و فرهنگ سازمانی",
        "questions": [
            "همکاران من به ایمنی یکدیگر اهمیت میدهند و اگر رفتار ناایمنی ببینند دوستانه تذکر میدهند.",
            "در این شرکت، ایمنی یک ارزش پایدار سازمانی است و با افزایش فشار تولید، اهمیت آن کاهش نمییابد.",
            "در این سازمان، رعایت ایمنی بخشی از فرهنگ انجام صحیح کار محسوب میشود، نه صرفاً یک الزام قانونی یا اداری یا فرار از جریمه.",
            "حتی وقتی سرپرست حضور ندارد، افراد اصول ایمنی را رعایت میکنند.",
        ],
    },
    {
        "name": "یادگیری سازمانی و بهبود مستمر",
        "questions": [
            "پس از وقوع حوادث و شبهحوادث، علل ریشهای آنها بهمنظور شناسایی و استفاده از درسآموختهها بررسی میشوند.",
            "نتایج و درسآموختههای حاصل از تحلیل حوادث و شبهحوادث برای پیشگیری از تکرار حوادث مشابه مورد استفاده قرار میگیرند.",
            "درسآموختههای حاصل از حوادث یک واحد یا خط تولید، با سایر واحدها/خطوط به اشتراک گذاشته میشود.",
            "با وجود تحلیل حوادث گذشته، مشکلات یا الگوهای ناایمن مشابه همچنان تکرار میشوند.",
            "مدیران در صورت وقوع خطا، آن را بهعنوان فرصتی برای یادگیری و بهبود عملکرد ایمنی در نظر میگیرند.",
        ],
    },
    {
        "name": "قوانین، رویهها و الزامات ایمنی",
        "questions": [
            "سازمان دارای سیاست ایمنی مکتوب و اهداف ایمنی مشخص و قابلسنجش است.",
            "اهداف ایمنی سازمان بهطور دورهای پایش و در صورت نیاز بهروزرسانی میشود.",
            "رویهها و دستورالعملهای ایمنی بهروز و بهصورت مستند در دسترس کارکنان هستند.",
            "دستورالعملها و رویههای ایمنی با نحوه واقعی انجام فعالیتهای کاری در محیط کار مطابقت دارند.",
            "دستورالعملهای ایمنی ساده و به زبان قابل فهم نوشته شده است.",
            "در صورت تغییر شرایط کاری یا شناسایی خطرات جدید، رویههای ایمنی مرتبط مورد بازنگری و اصلاح قرار میگیرند.",
        ],
    },
]

QUESTIONS = []
for dim_index, dim in enumerate(DIMENSIONS, start=1):
    for local_index, question in enumerate(dim["questions"], start=1):
        QUESTIONS.append({
            "number": len(QUESTIONS) + 1,
            "dimension_index": dim_index,
            "dimension": dim["name"],
            "local_index": local_index,
            "text": question,
        })

assert len(QUESTIONS) == 47, f"Expected 47 questions, got {len(QUESTIONS)}"

# فقط گویه 40 دارای جهت منفی است و برای محاسبه امتیاز معکوس می‌شود.
# متن این گویه در نسخه نهایی فایل: «... مشکلات یا الگوهای ناایمن مشابه همچنان تکرار میشوند.»
REVERSE_QUESTIONS = {40}


# ============================================================
# دیتابیس
# ============================================================

def db():
    return sqlite3.connect(DB_FILE)


def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL DEFAULT 'in_progress'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            response_id INTEGER NOT NULL,
            question_number INTEGER NOT NULL,
            dimension TEXT NOT NULL,
            answer_value INTEGER,
            answer_label TEXT NOT NULL,
            PRIMARY KEY (response_id, question_number)
        )
    """)

    con.commit()
    con.close()


# ============================================================
# وضعیت کاربر در حافظه
# ============================================================

# برای نسخه واقعی بهتر است وضعیت session هم در Redis/DB نگهداری شود.
SESSIONS = {}


def get_or_create_session(user):
    if user.id not in SESSIONS:
        con = db()
        cur = con.cursor()

        cur.execute("""
            INSERT INTO responses
            (telegram_user_id, username, first_name, started_at, status)
            VALUES (?, ?, ?, ?, 'in_progress')
        """, (
            user.id,
            user.username or "",
            user.first_name or "",
            datetime.now().isoformat(timespec="seconds"),
        ))

        response_id = cur.lastrowid
        con.commit()
        con.close()

        SESSIONS[user.id] = {
            "response_id": response_id,
            "current_index": 0,
            "answers": {},
        }

    return SESSIONS[user.id]


# ============================================================
# ابزارهای محاسبه
# ============================================================

def scored_value(question_number, value):
    if value is None:
        return None

    if question_number in REVERSE_QUESTIONS:
        return 6 - value

    return value


def calculate_results(answer_map):
    dimension_results = {}

    for dim in DIMENSIONS:
        nums = [
            q["number"]
            for q in QUESTIONS
            if q["dimension"] == dim["name"]
        ]

        values = []
        for n in nums:
            value = answer_map.get(n)
            value = scored_value(n, value)
            if value is not None:
                values.append(value)

        dimension_results[dim["name"]] = (
            round(sum(values) / len(values), 3) if values else None
        )

    all_values = [
        scored_value(q["number"], answer_map.get(q["number"]))
        for q in QUESTIONS
        if answer_map.get(q["number"]) is not None
    ]

    overall = round(sum(all_values) / len(all_values), 3) if all_values else None

    return dimension_results, overall


def maturity_level(score):
    # این تابع فعلاً فقط برای گزارش اختیاری است.
    # اگر در پایان‌نامه تقسیم‌بندی 5 سطحی خاصی تعیین کرده‌اید،
    # حدود آن را مطابق روش نهایی پایان‌نامه تغییر دهید.
    if score is None:
        return "محاسبه نشد"

    if score < 1.8:
        return "سطح 1"
    elif score < 2.6:
        return "سطح 2"
    elif score < 3.4:
        return "سطح 3"
    elif score < 4.2:
        return "سطح 4"
    return "سطح 5"


# ============================================================
# ذخیره CSV
# ============================================================

def export_csv():
    con = db()
    cur = con.cursor()

    cur.execute("""
        SELECT
            r.id,
            r.telegram_user_id,
            r.username,
            r.first_name,
            r.started_at,
            r.completed_at,
            a.question_number,
            a.dimension,
            a.answer_value,
            a.answer_label
        FROM responses r
        JOIN answers a ON a.response_id = r.id
        WHERE r.status = 'completed'
        ORDER BY r.id, a.question_number
    """)

    rows = cur.fetchall()
    con.close()

    headers = [
        "response_id",
        "telegram_user_id",
        "username",
        "first_name",
        "started_at",
        "completed_at",
        "question_number",
        "dimension",
        "answer_value",
        "answer_label",
    ]

    with open(CSV_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


# ============================================================
# پیام‌ها
# ============================================================

def question_keyboard(question_number):
    buttons = []

    for label, value in OPTIONS:
        callback = f"ans:{question_number}:{value if value is not None else 'NA'}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback)])

    return InlineKeyboardMarkup(buttons)


async def show_question(update, context, index):
    user = update.effective_user
    session = SESSIONS[user.id]

    q = QUESTIONS[index]

    text = (
        f"📋 پرسشنامه ارزیابی بلوغ فرهنگ ایمنی\n\n"
        f"**بعد {q['dimension_index']} از 8: {q['dimension']}**\n"
        f"سؤال {q['number']} از {len(QUESTIONS)}\n\n"
        f"{q['text']}\n\n"
        f"لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=question_keyboard(q["number"]),
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            text=text,
            reply_markup=question_keyboard(q["number"]),
            parse_mode="Markdown",
        )


# ============================================================
# دستورات
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # اگر قبلاً session فعال داشته، پرسشنامه جدید نساز.
    if user.id in SESSIONS:
        await update.message.reply_text(
            "یک پرسشنامه در حال تکمیل دارید.\n"
            "اگر می‌خواهید از ابتدا شروع کنید، /new را بزنید."
        )
        return

    text = (
        "سلام 🌱\n\n"
        "به پرسشنامه «ارزیابی سطح بلوغ فرهنگ ایمنی» خوش آمدید.\n\n"
        "این پرسشنامه شامل ۴۷ گویه در ۸ بعد است.\n"
        "لطفاً برای هر عبارت فقط یک گزینه را انتخاب کنید.\n\n"
        "اطلاعات پاسخ‌ها به‌صورت سیستمی ثبت می‌شود و برای تحلیل پژوهشی استفاده خواهد شد.\n\n"
        "برای شروع روی «شروع پرسشنامه» بزنید."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ شروع پرسشنامه", callback_data="start_survey")]
    ])

    await update.message.reply_text(text, reply_markup=keyboard)


async def new_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id in SESSIONS:
        old = SESSIONS.pop(user.id)

        con = db()
        con.execute(
            "UPDATE responses SET status='cancelled' WHERE id=?",
            (old["response_id"],)
        )
        con.commit()
        con.close()

    await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    session = SESSIONS.pop(user.id, None)

    if session:
        con = db()
        con.execute(
            "UPDATE responses SET status='cancelled' WHERE id=?",
            (session["response_id"],)
        )
        con.commit()
        con.close()

    await update.message.reply_text(
        "پرسشنامه لغو شد.\nبرای شروع مجدد /start را بزنید."
    )


# ============================================================
# پاسخ به دکمه‌ها
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    data = query.data

    if data == "start_survey":
        session = get_or_create_session(user)
        session["current_index"] = 0
        await show_question(update, context, 0)
        return

    if not data.startswith("ans:"):
        return

    try:
        _, question_number_str, value_str = data.split(":")
        question_number = int(question_number_str)
        value = None if value_str == "NA" else int(value_str)
    except ValueError:
        await query.edit_message_text("خطایی در ثبت پاسخ رخ داد. دوباره /start را بزنید.")
        return

    session = SESSIONS.get(user.id)

    if not session:
        await query.edit_message_text(
            "این پرسشنامه دیگر فعال نیست. لطفاً /start را بزنید."
        )
        return

    expected_question = QUESTIONS[session["current_index"]]["number"]

    if question_number != expected_question:
        await query.answer("لطفاً به سؤال فعلی پاسخ دهید.", show_alert=True)
        return

    # ذخیره پاسخ در حافظه
    session["answers"][question_number] = value
    q = QUESTIONS[session["current_index"]]

    # ذخیره پاسخ در DB
    con = db()
    con.execute("""
        INSERT OR REPLACE INTO answers
        (response_id, question_number, dimension, answer_value, answer_label)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["response_id"],
        question_number,
        q["dimension"],
        value,
        next(label for label, val in OPTIONS if val == value),
    ))
    con.commit()
    con.close()

    session["current_index"] += 1

    # سؤال بعدی
    if session["current_index"] < len(QUESTIONS):
        await show_question(update, context, session["current_index"])
        return

    # پایان
    await finish_survey(update, context)


async def finish_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = SESSIONS.get(user.id)

    answers = session["answers"]
    dimension_results, overall = calculate_results(answers)

    completed_at = datetime.now().isoformat(timespec="seconds")

    con = db()
    con.execute(
        "UPDATE responses SET completed_at=?, status='completed' WHERE id=?",
        (completed_at, session["response_id"])
    )
    con.commit()
    con.close()

    export_csv()

    # پیام پاسخ‌دهنده
    await update.callback_query.edit_message_text(
        "✅ پرسشنامه با موفقیت تکمیل شد.\n\n"
        "از همکاری شما سپاسگزاریم."
    )

    # گزارش برای مدیر
    if ADMIN_CHAT_ID:
        lines = [
            "📥 پاسخنامه جدید دریافت شد",
            "",
            f"کد پاسخ: {session['response_id']}",
            f"تعداد پاسخ‌های ثبت‌شده: {len(answers)}",
            "",
        ]

        for name, score in dimension_results.items():
            if score is None:
                lines.append(f"• {name}: محاسبه نشد")
            else:
                lines.append(
                    f"• {name}: {score:.3f}"
                )

        lines.extend([
            "",
            f"⭐ میانگین کل: {overall:.3f}" if overall is not None else "⭐ میانگین کل: محاسبه نشد",
            f"سطح محاسباتی: {maturity_level(overall)}",
            "",
            "📄 فایل CSV پاسخ‌ها در سرور به‌روزرسانی شد.",
        ])

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text="\n".join(lines),
        )

    # پاک کردن session
    SESSIONS.pop(user.id, None)


# ============================================================
# دستور مدیر برای گرفتن آمار
# ============================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("این دستور فقط برای مدیر ربات است.")
        return

    con = db()
    cur = con.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM responses WHERE status='completed'"
    )
    completed = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM responses WHERE status='in_progress'"
    )
    in_progress = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM responses WHERE status='cancelled'"
    )
    cancelled = cur.fetchone()[0]

    con.close()

    await update.message.reply_text(
        "📊 آمار ربات\n\n"
        f"پاسخنامه‌های تکمیل‌شده: {completed}\n"
        f"در حال تکمیل: {in_progress}\n"
        f"لغوشده: {cancelled}"
    )


async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("این دستور فقط برای مدیر ربات است.")
        return

    export_csv()

    with open(CSV_FILE, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=CSV_FILE,
            caption="📄 خروجی پاسخ‌های تکمیل‌شده"
        )


# ============================================================
# اجرای ربات
# ============================================================

def main():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN را تنظیم کنید. "
            "می‌توانید آن را به‌صورت Environment Variable قرار دهید."
        )

    if ADMIN_CHAT_ID == 0:
        raise RuntimeError(
            "ADMIN_CHAT_ID را تنظیم کنید."
        )

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new_survey))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("export", admin_export))

    app.add_handler(
        CallbackQueryHandler(button_handler)
    )

    print("Safety Culture Questionnaire Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
