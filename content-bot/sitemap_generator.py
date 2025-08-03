# sitemap_generator.py

import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# .env faylini yuklash (agar mavjud bo'lsa)
load_dotenv()

# --- SOZLAMALAR ---
FIREBASE_SERVICE_ACCOUNT_KEY_PATH = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY_PATH", "serviceAccountKey.json")
WEBSITE_BASE_URL = "https://evolvo-ai-website.onrender.com" 
OUTPUT_FILE = "sitemap.xml"

# --- Firebase'ga ulanish ---
try:
    cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_KEY_PATH)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase'ga muvaffaqiyatli ulanildi.")
except Exception as e:
    print(f"Firebase'ga ulanishda xatolik: {e}")
    db = None
    exit()

def generate_sitemap():
    """
    Firebase'dan ma'lumotlarni o'qiydi va sitemap.xml faylini yaratadi.
    """
    if not db:
        print("Ma'lumotlar bazasiga ulanish yo'q.")
        return

    urls = []
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Asosiy sahifalarni qo'shish
    static_pages = ["", "blog.html", "portfolio.html"]
    for page in static_pages:
        urls.append({
            "loc": f"{WEBSITE_BASE_URL}/{page if page else ''}",
            "lastmod": now_str,
            "changefreq": "weekly",
            "priority": "0.9" if page == "" else "0.8"
        })
        
    # 2. Blog postlarini qo'shish
    try:
        posts_ref = db.collection('posts').stream()
        post_count = 0
        for post in posts_ref:
            post_count += 1
            post_data = post.to_dict()
            lastmod = now_str
            # Xatolikni oldini olish uchun tekshiruv
            if 'createdAt' in post_data and hasattr(post_data['createdAt'], 'strftime'):
                lastmod = post_data['createdAt'].strftime("%Y-%m-%d")

            urls.append({
                "loc": f"{WEBSITE_BASE_URL}/post.html?id={post.id}",
                "lastmod": lastmod,
                "changefreq": "monthly",
                "priority": "1.0"
            })
        print(f"{post_count} ta maqola topildi.")
    except Exception as e:
        print(f"Blog postlarini o'qishda xatolik: {e}")

    # 3. Portfolio loyihalarini qo'shish
    try:
        portfolio_ref = db.collection('portfolio').stream()
        portfolio_count = 0
        for item in portfolio_ref:
            portfolio_count += 1
            item_data = item.to_dict()
            lastmod = now_str
            # Xatolikni oldini olish uchun tekshiruv
            if 'createdAt' in item_data and hasattr(item_data['createdAt'], 'strftime'):
                lastmod = item_data['createdAt'].strftime("%Y-%m-%d")

            urls.append({
                "loc": f"{WEBSITE_BASE_URL}/portfolio-item.html?id={item.id}",
                "lastmod": lastmod,
                "changefreq": "monthly",
                "priority": "0.7"
            })
        print(f"{portfolio_count} ta portfolio loyihasi topildi.")
    except Exception as e:
        print(f"Portfolio loyihalarini o'qishda xatolik: {e}")
        
    # 4. XML faylini yaratish
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for url_data in urls:
        xml_content += '  <url>\n'
        xml_content += f"    <loc>{url_data['loc']}</loc>\n"
        xml_content += f"    <lastmod>{url_data['lastmod']}</lastmod>\n"
        xml_content += f"    <changefreq>{url_data['changefreq']}</changefreq>\n"
        xml_content += f"    <priority>{url_data['priority']}</priority>\n"
        xml_content += '  </url>\n'
        
    xml_content += '</urlset>'
    
    # Faylga yozish
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(xml_content)
        print(f"'{OUTPUT_FILE}' fayli muvaffaqiyatli yaratildi. Unda {len(urls)} ta manzil mavjud.")
    except Exception as e:
        print(f"Faylga yozishda xatolik: {e}")

if __name__ == "__main__":
    generate_sitemap()
