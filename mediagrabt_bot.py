import os
import tempfile
import subprocess
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
)
import imageio_ffmpeg as ffmpeg_helper

# BOT token environment variabledan olinadi
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN muhit o'zgaruvchisi topilmadi. Render yoki serverda BOT_TOKEN qo'ying.")

# Maksimal fayl hajmi (45 MB)
FILE_LIMIT = 45 * 1024 * 1024

MSG = {
    "uz": {"checking": "⏳ Tekshirilmoqda...", "toolarge": "❗ Fayl juda katta.", "done": "✔ Mana video va audio:"},
    "ru": {"checking": "⏳ Проверяю...", "toolarge": "❗ Файл слишком большой.", "done": "✔ Вот видео и аудио:"},
    "tj": {"checking": "⏳ Санҷида истодаам...", "toolarge": "❗ Файл хеле калон аст.", "done": "✔ Омода шуд видео ва аудио:"}
}

user_lang = {}

def detect_lang(text: str):
    text = text.lower()
    if "привет" in text or "ссылка" in text: return "ru"
    if "салом" in text or "пайванд" in text: return "tj"
    return "uz"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("🇺🇿 O‘zbekcha", callback_data="uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="ru"),
        InlineKeyboardButton("🇹🇯 Тоҷикӣ", callback_data="tj")
    ]]
    await update.message.reply_text(
        "Assalomu alaykum, botimizga hush kelibsiz 😊\nMen Shohjahon tomonidan yasalgan!\n\nTilni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_lang[q.from_user.id] = q.data
    await q.edit_message_text(f"Til tanlandi: {q.data.upper()} ✅")

def download_video(url: str, outdir: str):
    template = os.path.join(outdir, "%(title).80s.%(ext)s")
    cmd = ["yt-dlp", "-o", template, "-f", "best", url]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    files = [os.path.join(outdir, f) for f in os.listdir(outdir)]
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0] if files else None

def convert_to_audio(video_path: str, outdir: str):
    base = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(outdir, f"{base}.mp3")

    # imageio-ffmpeg yordamida ffmpeg executable yo'lini olish
    ffmpeg_exe = ffmpeg_helper.get_exe()

    cmd = [ffmpeg_exe, "-i", video_path, "-vn", "-ab", "128k", "-ar", "44100", "-y", audio_path]
    proc = subprocess.run(cmd, capture_output=True)
    return audio_path if proc.returncode == 0 else None

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    lang = user_lang.get(update.message.from_user.id, detect_lang(text))

    if not text.startswith("http"):
        await update.message.reply_text("❗ Iltimos, to‘g‘ri link yuboring.")
        return

    await update.message.reply_text(MSG[lang]["checking"])

    with tempfile.TemporaryDirectory() as tmp:
        video_file = download_video(text, tmp)
        if not video_file:
            await update.message.reply_text("❗ Video yuklashda xatolik!")
            return

        if os.path.getsize(video_file) > FILE_LIMIT:
            await update.message.reply_text(MSG[lang]["toolarge"])
            return

        audio_file = convert_to_audio(video_file, tmp)
        if not audio_file:
            await update.message.reply_text("❗ Audio yaratishda xatolik!")
            return

        await update.message.reply_text(MSG[lang]["done"])
        try:
            with open(video_file, "rb") as f:
                await update.message.reply_document(document=InputFile(f))
            with open(audio_file, "rb") as f:
                await update.message.reply_document(document=InputFile(f))
        except Exception as e:
            await update.message.reply_text(f"❗ Fayl yuborishda xatolik: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print("▶ mediagrabt_bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
