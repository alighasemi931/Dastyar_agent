# scripts/fetch_reviews_orm.py
import requests
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.model import IPhoneProduct, Base  # مدل‌هایی که قبلاً ساختیم

# --- settings ---
DB_NAME = "sqlite:///digikala_products.db"
REVIEWS_API_BASE = "https://api.digikala.com/v1/rate-review/products/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}

engine = create_engine(DB_NAME)
SessionLocal = sessionmaker(bind=engine)

# ----------------------------
#  function to convert comments to text
# ----------------------------
def build_readable_reviews(comments):
    """لیست نظرات را به رشته‌ی خوانا تبدیل می‌کند."""
    lines = []
    for i, comment in enumerate(comments, 1):
        rate = comment.get("rate", "")
        body = comment.get("body", "").strip()
        user_type = "🛒 خریدار" if comment.get("review_user_type") == "buyer" else "👤 کاربر"
        lines.append(f"{i}. {user_type} | امتیاز: {rate}\n{body}\n")

    if not lines:
        return "بدون نظر ثبت‌شده."
    return "\n".join(lines)


# ----------------------------
#  main function to fetch and store
# ----------------------------
def fetch_and_store_all_reviews(delay=1, max_pages=2):
    """دریافت نظرات تمام آیفون‌ها و ذخیره در ستون reviews_text."""
    session = SessionLocal()
    products = session.query(IPhoneProduct).all()
    total = len(products)
    print(f"🔍 تعداد محصولات برای بررسی: {total}")

    for idx, product in enumerate(products, start=1):
        product_id = product.product_id
        print(f"\n({idx}/{total}) دریافت نظرات محصول {product_id}...")

        all_comments = []
        for page in range(1, max_pages + 1):
            url = f"{REVIEWS_API_BASE}{product_id}/?sort=buyers&page={page}"
            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
                data = response.json()
                comments = data.get("data", {}).get("comments", [])
                if not comments:
                    break
                all_comments.extend(comments)
                print(f"  ✅ صفحه {page}: {len(comments)} نظر دریافت شد.")
                time.sleep(0.5)
            except Exception as e:
                print(f"  ❌ خطا در دریافت نظرات صفحه {page} برای محصول {product_id}: {e}")
                break

    # Convert and store in ORM
        readable_reviews = build_readable_reviews(all_comments)
        product.reviews_text = readable_reviews

        try:
            session.commit()
            print(f"  💾 ذخیره شد ({len(all_comments)} نظر).")
        except Exception as e:
            session.rollback()
            print(f"❌ خطا در ذخیره محصول {product_id}: {e}")

        time.sleep(delay)

    session.close()
    print("\n✨ همه نظرات پردازش و ذخیره شدند.")


# ----------------------------
#  direct execution
# ----------------------------
if __name__ == "__main__":
    # Ensure tables exist if 'reviews_text' column is missing in model
    Base.metadata.create_all(engine)
    fetch_and_store_all_reviews(delay=1, max_pages=2)
