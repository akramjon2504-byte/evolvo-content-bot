# bot.py

import os
import logging
import asyncio
import feedparser
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import json
import numpy as np
import threading
from flask import Flask

# .env faylidagi o'zgaruvchilarni yuklash
load_dotenv()

# --- Veb-server qismi (Render uchun "hiyla") ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Evolvo AI Content Bot is alive!"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))

# RSS Manbalari Ro'yxati
RSS_FEEDS = {
    'AI General News': 'https://www.technologyreview.com/feed/',
    'Web Development': 'https://www.smashingmagazine.com/feed/',
    'The Rundown AI': 'https://www.therundown.ai/rss.xml',
    'Ben\'s Bites': 'https://bensbites.co/feed',
    'Prompt Engineering': 'https://www.promptingguide.ai/rss.xml'
}

# Loglashni sozlash
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Firebase'ga ulanish
try:
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Firebase'ga muvaffaqiyatli ulanildi.")
except Exception as e:
    logger.error(f"Firebase'ga ulanishda xatolik: {e}")
    db = None

# Google Gemini modelini sozlash
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# --- YORDAMCHI FUNKSIYALAR ---
def is_admin(update: Update) -> bool:
    return update.effective_user.id == ADMIN_USER_ID

async def is_post_exists(post_link: str) -> bool:
    if not db: return True
    posts_ref = db.collection('posts')
    query = posts_ref.where('original_link', '==', post_link).limit(1).stream()
    return len(list(query)) > 0

def extract_image_from_html(entry):
    if 'media_content' in entry and entry.media_content:
        for media in entry.media_content:
            if 'url' in media and media.get('medium') == 'image': return media['url']
    if 'links' in entry:
        for link in entry.links:
            if link.get('rel') == 'enclosure' and 'image' in link.get('type', ''): return link.href
    content = entry.get('content', [{}])[0].get('value') or entry.summary
    if not content: return None
    soup = BeautifulSoup(content, 'html.parser')
    img_tag = soup.find('img')
    return img_tag['src'] if img_tag and 'src' in img_tag.attrs else None

def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0: return 0
    return dot_product / (norm_vec1 * norm_vec2)

async def is_semantically_similar(new_title: str) -> bool:
    if not db: return True
    try:
        posts_ref = db.collection('posts').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(50)
        docs = posts_ref.stream()
        existing_vectors = [doc.to_dict().get('title_embedding') for doc in docs if doc.to_dict().get('title_embedding')]
        if not existing_vectors: return False

        new_embedding_result = await genai.embed_content_async(model='models/text-embedding-004', content=new_title, task_type="RETRIEVAL_DOCUMENT")
        new_vector = new_embedding_result['embedding']

        for vector in existing_vectors:
            if cosine_similarity(new_vector, vector) > 0.90:
                logger.info("Takroriy kontent topildi.")
                return True
        return False
    except Exception as e:
        logger.error(f"Semantik o'xshashlikni tekshirishda xatolik: {e}")
        return False

# --- ASOSIY MANTIQ ---
async def fetch_and_process_feeds(context: ContextTypes.DEFAULT_TYPE, manual_run: bool = False):
    if not db:
        if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text="Xatolik: Firebase'ga ulanib bo'lmadi.")
        return
    if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text="Yangiliklarni qidirish boshlandi...")
    all_new_entries = []
    for category, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            if not await is_post_exists(entry.link): all_new_entries.append(entry)
    if not all_new_entries:
        if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text="Qidiruv yakunlandi. Yangi maqolalar topilmadi."); return
    latest_entry = sorted(all_new_entries, key=lambda x: x.published_parsed, reverse=True)[0]
    if await is_semantically_similar(latest_entry.title):
        if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text=f"Yangi maqola topildi, lekin u mazmunan takroriy: {latest_entry.title}"); return
    try:
        if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text=f"Yangi maqola topildi: {latest_entry.title}\nQayta ishlanmoqda...")
        prompt = f"""
        Sen "Evolvo AI" kompaniyasining nomidan yozuvchi professional texnik tarjimon va kontent-muharrirsan. Sening vazifang - quyidagi inglizcha maqoladan O'zbekiston auditoriyasi uchun chuqur, batafsil va tushunarli kontent yaratish. Original manbadagi "In today's download..." kabi iboralarni ishlatma, balki o'z nomingdan tahliliy maqola yoz.

        Natijani faqatgina JSON formatida, quyidagi aniq strukturada qaytar. Hech qanday ortiqcha matn yoki izoh qo'shma.

        {{
          "title": "SEO uchun optimallashtirilgan, jozibali o'zbekcha sarlavha.",
          "summary": "Veb-sayt uchun maqolaning asosiy g'oyasini ochib beruvchi 2-3 gaplik qisqacha mazmun.",
          "content_markdown": "Veb-sayt uchun maqolaning BATAFSIL va TO'LIQ tarjimasi. Matn kamida 4-5 paragrafdan iborat bo'lishi kerak. Uni o'qish uchun qulay qilib, paragraflarga ajrat, kerakli joylarda `- Ro'yxat elementi` formatini ishlat va eng muhim joylarni `**qalin shrift**` bilan belgilab chiq.",
          "telegram_post": "Telegram kanal uchun tayyor, qiziqarli matn. Unda sarlavha, mavzuni ochib beruvchi 2-3 ta asosiy fikr (emoji bilan belgilangan ro'yxat) va 'Batafsil:' chaqiruvi bo'lsin.",
          "category": "Maqolaga mos keladigan bitta aniq kategoriya (masalan, 'Sun\\'iy Intellekt', 'Veb Dasturlash', 'Dizayn')",
          "hashtags": "Telegram kanal uchun 3-4 ta mos heshteg (masalan, '#AI #dasturlash #yangiliklar')"
        }}

        Original sarlavha: {entry.title}
        Original matn: {BeautifulSoup(entry.summary, 'html.parser').get_text()}
        """
        response = await gemini_model.generate_content_async(prompt)
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
        post_json = json.loads(cleaned_response)
        title_embedding_result = await genai.embed_content_async(model='models/text-embedding-004', content=post_json.get('title'), task_type="RETRIEVAL_DOCUMENT")
        post_data = {
            'title': post_json.get('title'), 'summary': post_json.get('summary'), 'content': post_json.get('content_markdown'),
            'category': post_json.get('category'), 'imageUrl': extract_image_from_html(latest_entry),
            'original_link': latest_entry.link, 'createdAt': firestore.SERVER_TIMESTAMP,
            'title_embedding': title_embedding_result['embedding']
        }
        doc_ref = db.collection('posts').add(post_data)
        new_post_id = doc_ref[1].id
        website_post_url = f"https://evolvo-ai-website.onrender.com/post.html?id={new_post_id}"
        final_telegram_message = f"{post_json.get('telegram_post')}\n\nBatafsil: [Veb-saytda]({website_post_url})\n\n{post_json.get('hashtags')}"
        if post_data['imageUrl']:
            await context.bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=post_data['imageUrl'], caption=final_telegram_message, parse_mode=ParseMode.MARKDOWN)
        else:
            await context.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=final_telegram_message, parse_mode=ParseMode.MARKDOWN)
        if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text=f"✅ '{post_json.get('title')}' maqolasi saytga va kanalga muvaffaqiyatli joylandi!")
    except Exception as e:
        logger.error(f"Maqolani qayta ishlashda xatolik: {e}")
        if manual_run: await context.bot.send_message(chat_id=ADMIN_USER_ID, text=f"⚠️ Xatolik: {latest_entry.title}\n{e}")

async def scheduled_fetch(context: ContextTypes.DEFAULT_TYPE):
    await fetch_and_process_feeds(context, manual_run=False)

# --- BOT BUYRUQLARI ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): await update.message.reply_text("Kechirasiz, bu bot faqat adminlar uchun."); return
    await update.message.reply_text("Salom, Admin! Men Evolvo AI kontent botiman...")

async def fetch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): await update.message.reply_text("Bu buyruq faqat adminlar uchun."); return
    asyncio.create_task(fetch_and_process_feeds(context, manual_run=True))
    await update.message.reply_text("Jarayon boshlandi. Natijalar shu yerga yuboriladi.")

def main():
    # Veb-serverni alohida oqimda (thread) ishga tushirish
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Asosiy bot ilovasini ishga tushirish
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    job_queue = application.job_queue
    job_queue.run_repeating(scheduled_fetch, interval=3600, first=10)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("fetch", fetch_command))
    logger.info("Kontent bot ishga tushdi... (Avtomatik rejimda)")
    application.run_polling()

if __name__ == "__main__":
    main()
