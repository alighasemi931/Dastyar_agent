# scripts/fetch_full_product_data_orm.py
import requests
import json
import time
from sqlalchemy.orm import Session
from sqlalchemy import inspect
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from databases.database import SessionLocal, engine
from models.model import Base, IPHONE_PRODUCTS, WATCH_PRODUCTS, IPHONE_COLORS, WATCH_COLORS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}

IPHONE_API = "https://api.digikala.com/v1/categories/mobile-phone/brands/apple/search/"
WATCH_API = "https://api.digikala.com/v1/categories/smart-watch/brands/apple/search/"
IPHONE_DETAILS_API = "https://api.digikala.com/v2/product/"
WATCH_DETAILS_API = "https://api.digikala.com/v2/product/"
IPHONE_REVIEWS_API = "https://api.digikala.com/v1/rate-review/products/"
WATCH_REVIEWS_API = "https://api.digikala.com/v1/rate-review/products/"

# ==========================
# تابع کمکی برای متن خوانا از نظرات
# ==========================
def build_readable_reviews(comments):
    lines = []
    for i, comment in enumerate(comments, 1):
        rate = comment.get("rate", "")
        body = comment.get("body", "").strip()
        user_type = "🛒 خریدار" if comment.get("review_user_type") == "buyer" else "👤 کاربر"
        lines.append(f"{i}. {user_type} | امتیاز: {rate}\n{body}\n")
    return "\n".join(lines) if lines else "بدون نظر ثبت‌شده."

# ==========================
# بررسی ستون در جدول
# ==========================
def ensure_column(model, column_name):
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(model.__tablename__)]
    if column_name not in columns:
        print(f"⚠️ ستون {column_name} در جدول {model.__tablename__} وجود ندارد.")
    else:
        print(f"ℹ️ ستون {column_name} در جدول {model.__tablename__} موجود است.")

# ==========================
# جمع‌آوری محصولات و رنگ‌ها
# ==========================
def fetch_and_store_products(api_url, product_model, color_model, max_pages=2):
    session: Session = SessionLocal()
    total_added = 0

    for page in range(1, max_pages + 1):
        url = f"{api_url}?page={page}"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            # بررسی ساختار داده‌ها
            products_list = []
            data_content = data.get("data", {})
            if isinstance(data_content, dict):
                products_list = data_content.get("products", [])
            elif isinstance(data_content, list):
                products_list = data_content

            if not products_list:
                break

            for p in products_list:
                pid = p.get("id")
                title_fa = p.get("title_fa")
                relative_url = p.get("url", {}).get("uri") if isinstance(p.get("url"), dict) else None

                selling_price = None
                default_variant = p.get("default_variant")
                if isinstance(default_variant, dict):
                    selling_price = default_variant.get("price", {}).get("selling_price")
                elif isinstance(default_variant, list) and len(default_variant) > 0:
                    selling_price = default_variant[0].get("price", {}).get("selling_price")

                if not (pid and title_fa and relative_url and selling_price):
                    continue

                # ایجاد یا آپدیت محصول
                db_product = session.query(product_model).filter_by(product_id=pid).first()
                if not db_product:
                    db_product = product_model(
                        product_id=pid,
                        title_fa=title_fa,
                        relative_url=f"https://www.digikala.com{relative_url}",
                        selling_price=selling_price
                    )
                    session.add(db_product)
                    total_added += 1
                else:
                    db_product.title_fa = title_fa
                    db_product.relative_url = f"https://www.digikala.com{relative_url}"
                    db_product.selling_price = selling_price

                # ذخیره رنگ‌ها
                colors = p.get("colors", [])
                for c in colors:
                    color_title = c.get("title")
                    if color_title and not session.query(color_model).filter_by(product_id=pid, title=color_title).first():
                        session.add(color_model(product_id=pid, title=color_title))
            
            session.commit()
            print(f"✅ صفحه {page} پردازش شد. محصولات اضافه‌شده: {total_added}")
            time.sleep(1)

        except Exception as e:
            print(f"❌ خطا در صفحه {page}: {e}")
            session.rollback()
    session.close()
    print(f"✨ جمع‌آوری محصولات و رنگ‌ها پایان یافت. مجموع محصولات جدید: {total_added}")

# ==========================
# جمع‌آوری مشخصات و نظرات
# ==========================
def fetch_full_product_data(product_model, color_model, details_api, reviews_api, delay_specs=1, delay_reviews=1, max_pages=2):
    session: Session = SessionLocal()
    products = session.query(product_model).all()
    print(f"🔍 تعداد محصولات برای پردازش: {len(products)}")

    for idx, product in enumerate(products, start=1):
        pid = product.product_id
        print(f"\n({idx}/{len(products)}) پردازش محصول {pid} ...")

        # دریافت جزئیات محصول
        try:
            r = requests.get(f"{details_api}{pid}/", headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()

            # ذخیره رنگ‌ها از جزئیات
            colors = data.get("data", {}).get("product", {}).get("colors", [])
            for c in colors:
                title = c.get("title")
                if title and not session.query(color_model).filter_by(product_id=pid, title=title).first():
                    session.add(color_model(product_id=pid, title=title))
            session.commit()

            # ذخیره مشخصات
            specs = data.get("data", {}).get("product", {}).get("specifications", [])
            if specs and getattr(product, "specifications", None) in (None, ""):
                product.specifications = json.dumps(specs, ensure_ascii=False)
                session.commit()
                print(f"✅ مشخصات ذخیره شد.")
            time.sleep(delay_specs)

        except Exception as e:
            print(f"❌ خطا در دریافت جزئیات محصول {pid}: {e}")
            session.rollback()

        # دریافت نظرات
        try:
            all_comments = []
            for page in range(1, max_pages + 1):
                url = f"{reviews_api}{pid}/?sort=buyers&page={page}"
                r = requests.get(url, headers=HEADERS, timeout=10)
                r.raise_for_status()
                comments = r.json().get("data", {}).get("comments", [])
                if not comments:
                    break
                all_comments.extend(comments)
                time.sleep(0.5)

            product.reviews_text = build_readable_reviews(all_comments)
            session.commit()
            print(f"💾 نظرات ذخیره شد ({len(all_comments)} نظر).")
            time.sleep(delay_reviews)
        except Exception as e:
            print(f"❌ خطا در دریافت یا ذخیره نظرات محصول {pid}: {e}")
            session.rollback()

    session.close()
    print("\n✨ عملیات کامل برای همه محصولات پایان یافت.")

# ==========================
# اجرای مستقیم
# ==========================
if __name__ == "__main__":
    # ایجاد جداول در صورت عدم وجود
    Base.metadata.create_all(engine)
    print("✅ جدول‌ها ایجاد شدند (اگر وجود نداشتند).")

    # بررسی ستون‌ها
    ensure_column(IPHONE_PRODUCTS, "specifications")
    ensure_column(IPHONE_PRODUCTS, "reviews_text")
    ensure_column(WATCH_PRODUCTS, "specifications")
    ensure_column(WATCH_PRODUCTS, "reviews_text")

    # جمع‌آوری محصولات و رنگ‌ها
    print("\n=== جمع‌آوری محصولات آیفون ===")
    fetch_and_store_products(IPHONE_API, IPHONE_PRODUCTS, IPHONE_COLORS, max_pages=2)

    print("\n=== جمع‌آوری محصولات ساعت ===")
    fetch_and_store_products(WATCH_API, WATCH_PRODUCTS, WATCH_COLORS, max_pages=2)

    # دریافت مشخصات و نظرات
    print("\n=== پردازش آیفون‌ها ===")
    fetch_full_product_data(IPHONE_PRODUCTS, IPHONE_COLORS, IPHONE_DETAILS_API, IPHONE_REVIEWS_API)

    print("\n=== پردازش ساعت‌ها ===")
    fetch_full_product_data(WATCH_PRODUCTS, WATCH_COLORS, WATCH_DETAILS_API, WATCH_REVIEWS_API)
