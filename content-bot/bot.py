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

# ... (qolgan barcha kodlar avvalgidek qoladi) ...

# --- ASOSIY FUNKSIYA ---
def main() -> None:
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

# ... (qolgan barcha funksiyalar (fetch_and_process_feeds, start, va hokazo) avvalgi koddagidek saqlanib qoladi) ...
