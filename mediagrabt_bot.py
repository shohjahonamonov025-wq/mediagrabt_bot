import os
import tempfile
import subprocess
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# --- BOT TOKEN ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi! Render Environment ichiga qo‘ying.")

# Fayl limiti
FILE_LIMIT = 45 * 1024 * 1024

MSG = {
    "uz": {"checking": "Tekshirilmoqda...", "toolarge": "Fayl juda katta.", "done": "Mana video va audio:"},
    "ru": {"checking": "Проверяю...", "toolarge": "Файл слишком большой.", "done": "Вот видео и аудио:"},
    "tj": {"checking": "Санҷида истодаам...", "toolarge": "Файл хеле калон аст.", "done": "Омода шуд видео ва аудио:"}
}

user_lang = {}  # Foydalanuvchi tilini saqlaydi


def detect_lang(text):
    t = text.lower()
    if "salom" in t or "video" in t: return "uz"
    if "привет" in t or "видео" in t: return "ru"
    if "салом" in t or "видео" in t: return "tj"
    return "uz"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O‘zbekcha", callback_data="uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
            InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="tj")
        ]
    ]
    await update.message.reply_text(
        "Assalomu alaykum, botimizga hush kelibsiz 😊\n"
        "Men Shohjahon tomonidan yasalgan!\n\n"
        "Iltimos, tilni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = q.data
    user_lang[q.from_user.id] = lang
    await q.edit_message_text(f"Til tanlandi: {lang.upper()} ✅")


def download_video(url, outdir):
    template = os.path.join(outdir, "%(title).80s.%(ext)s")
    cmd = ["yt-dlp", "-o", template, "-f", "best", url]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None

    files = [os.path.join(outdir, f) for f in os.listdir(outdir)]
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def convert_to_audio(video, outdir):
    base = os.path.splitext(os.path.basename(video))[0]
    audio = os.path.join(outdir, f"{base}.mp3")

    cmd = ["ffmpeg", "-i", video, "-vn", "-ab", "128k", "-ar", "44100", "-y", audio]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        return None

    return audio


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lang = user_lang.get(update.message.from_user.id, detect_lang(text))

    if not text.startswith("http"):
        await update.message.reply_text("Iltimos, to‘g‘ri link yuboring.")
        return

    await update.message.reply_text(MSG[lang]["checking"])

    with tempfile.TemporaryDirectory() as tmp:
        video = download_video(text, tmp)
        if not video:
            await update.message.reply_text("Xatolik yuz berdi.")
            return

        if os.path.getsize(video) > FILE_LIMIT:
            await update.message.reply_text(MSG[lang]["toolarge"])
            return

        audio = convert_to_audio(video, tmp)
        if not audio:
            await update.message.reply_text("Audio yaratishda xatolik.")
            return

        await update.message.reply_text(MSG[lang]["done"])

        with open(video, "rb") as v:
            await update.message.reply_document(InputFile(v, filename=os.path.basename(video)))

        with open(audio, "rb") as a:
            await update.message.reply_document(InputFile(a, filename=os.path.basename(audio)))


def main():
    print("BOT ISHGA TUSHDI...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    app.run_polling()


if __name__ == "__main__":
    main()

