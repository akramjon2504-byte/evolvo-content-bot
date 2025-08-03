# Content Bot

RSS orqali yangiliklarni yig'ib, ularni AI yordamida qayta ishlab, Telegram kanaliga joylovchi bot.

## Tavsif

Ushbu loyiha quyidagi vazifalarni bajaradi:
- RSS feedlaridan yangiliklarni yig'ish
- Google Generative AI yordamida kontentni qayta ishlash
- Yangiliklarni Firebase Firestore'da saqlash
- Telegram kanaliga avtomatik post qo'shish
- Veb-sayt uchun sitemap yaratish

## Talablar

- Python 3.8+
- Python paketlari (`requirements.txt` faylida keltirilgan)
- Google Cloud API kaliti (Gemini uchun)
- Telegram Bot Tokeni
- Firebase Service Account fayli

## O'rnatish

1. Repozitoriyani klonlang:
   ```bash
   git clone https://github.com/yourusername/content-bot.git
   cd content-bot
   ```

2. Virtual muhit yarating va faollashtiring:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows uchun
   # yoki
   source .venv/bin/activate  # Linux/Mac uchun
   ```

3. Kerakli paketlarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```

4. `.env` faylini yarating va sozlang:
   ```env
   TELEGRAM_TOKEN=your_telegram_bot_token
   GEMINI_API_KEY=your_gemini_api_key
   FIREBASE_SERVICE_ACCOUNT_KEY_PATH=serviceAccountKey.json
   TELEGRAM_CHANNEL_ID=@your_channel
   ADMIN_USER_ID=your_telegram_user_id
   ```

5. `serviceAccountKey.json` faylini Firebase konsolidan yuklab oling va loyiha ildiziga joylang.

## Foydalanish

1. Botni ishga tushiring:
   ```bash
   python bot.py
   ```

2. Sitemap yaratish uchun:
   ```bash
   python sitemap_generator.py
   ```

## Litsenziya

MIT
