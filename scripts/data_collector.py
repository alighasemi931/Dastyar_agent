# scripts/data_collector.py
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
# Helper: build readable review text
# ==========================
def build_readable_reviews(comments):
    lines = []
    for i, comment in enumerate(comments, 1):
        rate = comment.get("rate", "")
        body = comment.get("body", "").strip()
        user_type = "🛒 Buyer" if comment.get("review_user_type") == "buyer" else "👤 User"
        lines.append(f"{i}. {user_type} | Rating: {rate}\n{body}\n")
    return "\n".join(lines) if lines else "No reviews."

# ==========================
# Check column existence in table
# ==========================
def ensure_column(model, column_name):
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(model.__tablename__)]
    if column_name not in columns:
        print(f"⚠️ Column {column_name} does not exist in table {model.__tablename__}.")
    else:
        print(f"ℹ️ Column {column_name} exists in table {model.__tablename__}.")

# ==========================
# Collect products and colors
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
            
            # Check data structure
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

                # Create or update product
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

                # Store colors
                colors = p.get("colors", [])
                for c in colors:
                    color_title = c.get("title")
                    if color_title and not session.query(color_model).filter_by(product_id=pid, title=color_title).first():
                        session.add(color_model(product_id=pid, title=color_title))
            
            session.commit()
            print(f"✅ Page {page} processed. Products added: {total_added}")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            session.rollback()
    session.close()
    print(f"✨ Finished collecting products and colors. Total new products: {total_added}")

# ==========================
# Collect specifications and reviews
# ==========================
def fetch_full_product_data(product_model, color_model, details_api, reviews_api, delay_specs=1, delay_reviews=1, max_pages=2):
    session: Session = SessionLocal()
    products = session.query(product_model).all()
    print(f"🔍 Products to process: {len(products)}")

    for idx, product in enumerate(products, start=1):
        pid = product.product_id
        print(f"\nProcessing product {pid} ({idx}/{len(products)}) ...")

        # Fetch product details
        try:
            r = requests.get(f"{details_api}{pid}/", headers=HEADERS, timeout=10)
            r.raise_for_status()
            data = r.json()

            # Store colors from details
            colors = data.get("data", {}).get("product", {}).get("colors", [])
            for c in colors:
                title = c.get("title")
                if title and not session.query(color_model).filter_by(product_id=pid, title=title).first():
                    session.add(color_model(product_id=pid, title=title))
            session.commit()

            # Store specifications
            specs = data.get("data", {}).get("product", {}).get("specifications", [])
            if specs and getattr(product, "specifications", None) in (None, ""):
                product.specifications = json.dumps(specs, ensure_ascii=False)
                session.commit()
                print(f"✅ Specifications saved.")
            time.sleep(delay_specs)

        except Exception as e:
            print(f"❌ Error fetching details for product {pid}: {e}")
            session.rollback()

        # Fetch reviews
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
            print(f"💾 Reviews saved ({len(all_comments)} comments).")
            time.sleep(delay_reviews)
        except Exception as e:
            print(f"❌ Error fetching/saving reviews for product {pid}: {e}")
            session.rollback()

    session.close()
    print("\n✨ Completed operations for all products.")

# ==========================
# Direct execution
# ==========================
if __name__ == "__main__":
    # Create tables if they don't exist
    Base.metadata.create_all(engine)
    print("✅ Tables created (if they did not exist).")

    # Check required columns
    ensure_column(IPHONE_PRODUCTS, "specifications")
    ensure_column(IPHONE_PRODUCTS, "reviews_text")
    ensure_column(WATCH_PRODUCTS, "specifications")
    ensure_column(WATCH_PRODUCTS, "reviews_text")

    # Collect products and colors
    print("\n=== Collecting iPhone products ===")
    fetch_and_store_products(IPHONE_API, IPHONE_PRODUCTS, IPHONE_COLORS, max_pages=2)

    print("\n=== Collecting Watch products ===")
    fetch_and_store_products(WATCH_API, WATCH_PRODUCTS, WATCH_COLORS, max_pages=2)

    # Fetch specifications and reviews
    print("\n=== Processing iPhones ===")
    fetch_full_product_data(IPHONE_PRODUCTS, IPHONE_COLORS, IPHONE_DETAILS_API, IPHONE_REVIEWS_API)

    print("\n=== Processing Watches ===")
    fetch_full_product_data(WATCH_PRODUCTS, WATCH_COLORS, WATCH_DETAILS_API, WATCH_REVIEWS_API)
