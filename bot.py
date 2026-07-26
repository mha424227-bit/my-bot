import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp

# خادم وهمي لإبقاء الخدمة تعمل على Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# التوكن الخاص بك
BOT_TOKEN = "8635974959:AAHkFUwW5A91w8vG-v-IjznD0OUId1TOuAc"
bot = telebot.TeleBot(BOT_TOKEN)

user_links = {}

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.reply_to(message, "أهلاً بك! أرسل لي رابط أي فيديو وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("http"))
def handle_link(message):
    url = message.text.strip()
    user_links[message.chat.id] = url

    markup = InlineKeyboardMarkup()
    btn_mp4 = InlineKeyboardButton("📹 فيديو (MP4)", callback_data="dl_mp4")
    btn_mp3 = InlineKeyboardButton("🎧 صوت (MP3)", callback_data="dl_mp3")
    markup.row(btn_mp4, btn_mp3)

    bot.reply_to(message, "اختر صيغة التحميل المطلوبة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["dl_mp4", "dl_mp3"])
def process_download(call):
    chat_id = call.message.chat.id
    url = user_links.get(chat_id)

    if not url:
        bot.answer_callback_query(call.id, "حدث خطأ! أرسل الرابط من جديد.")
        return

    is_mp3 = call.data == "dl_mp3"
    bot.answer_callback_query(call.id, "بدأت عملية التحميل...")
    status_msg = bot.send_message(chat_id, "⏳ جاري التحميل والمعالجة...")

    output_filename = f"file_{chat_id}.%(ext)s"

    ydl_opts = {
        'outtmpl': output_filename,
        'maxfilesize': 50 * 1024 * 1024,
        'quiet': True,
    }

    if is_mp3:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if is_mp3:
                filename = os.path.splitext(filename)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if is_mp3:
                bot.send_audio(chat_id, f, caption="تم التحميل بنجاح 🎧")
            else:
                bot.send_video(chat_id, f, caption="تم التحميل بنجاح 📹")

        if os.path.exists(filename):
            os.remove(filename)

        bot.delete_message(chat_id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {str(e)}", chat_id, status_msg.message_id)

bot.infinity_polling()
