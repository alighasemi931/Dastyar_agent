# scripts/watch_reviews_orm.py
import requests
import time
from sqlalchemy.orm import Session
from databases.database import SessionLocal, engine
from models.model import WatchProduct

REVIEWS_API_BASE = "https://api.digikala.com/v1/rate-review/products/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}


def build_readable_reviews(comments):
    """لیست نظرات را به صورت رشته‌ی خوانا و قالب‌بندی‌شده تبدیل می‌کند."""
    lines = []
    for i, comment in enumerate(comments, 1):
        rate = comment.get("rate", "")
        body = comment.get("body", "").strip()
        user_type = "🛒 خریدار" if comment.get("review_user_type") == "buyer" else "👤 کاربر"
        lines.append(f"{i}. {user_type} | امتیاز: {rate}\n{body}\n")

    return "\n".join(lines) if lines else "بدون نظر ثبت‌شده."


def fetch_and_store_all_reviews(delay=1, max_pages=2):
    """گرفتن نظرات تمام محصولات و ذخیره‌ی آن‌ها در ستون reviews_text."""
    session: Session = SessionLocal()
    try:
        products = session.query(WatchProduct).all()
        total = len(products)
        print(f"🔍 تعداد محصولات برای بررسی: {total}")

        for idx, product in enumerate(products, 1):
            print(f"\n({idx}/{total}) دریافت نظرات محصول {product.product_id}...")
            all_comments = []

            for page in range(1, max_pages + 1):
                url = f"{REVIEWS_API_BASE}{product.product_id}/?sort=buyers&page={page}"
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
                    print(f"  ❌ خطا در دریافت نظرات صفحه {page} برای محصول {product.product_id}: {e}")
                    break

            # Save reviews as readable text
            product.reviews_text = build_readable_reviews(all_comments)
            try:
                session.commit()
                print(f"  💾 ذخیره شد ({len(all_comments)} نظر).")
            except Exception as e:
                session.rollback()
                print(f"❌ خطا در ذخیره محصول {product.product_id}: {e}")

            time.sleep(delay)
    finally:
        session.close()
        print("\n✨ همه نظرات پردازش و ذخیره شدند.")


if __name__ == "__main__":
    fetch_and_store_all_reviews(delay=1, max_pages=2)
