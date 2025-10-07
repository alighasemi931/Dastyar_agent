# scripts/apple_watch_orm.py
import requests
import time
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# --- تنظیمات ---
DB_URL = "sqlite:///digikala_products.db"
API_URL_BASE = "https://api.digikala.com/v1/categories/smart-watch/brands/apple/search/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Accept': 'application/json'
}

Base = declarative_base()
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)


# -----------------------
# مدل‌ها
# -----------------------
class WatchProduct(Base):
    __tablename__ = "watch_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True)
    title_fa = Column(Text)
    relative_url = Column(Text)
    selling_price = Column(Integer)

    colors = relationship("WatchColor", back_populates="product", cascade="all, delete-orphan")


class WatchColor(Base):
    __tablename__ = "watch_colors"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("watch_products.product_id"))
    title = Column(Text)

    product = relationship("WatchProduct", back_populates="colors")


# -----------------------
# ساخت دیتابیس
# -----------------------
def setup_database():
    Base.metadata.create_all(engine)
    print(f"✅ دیتابیس و جداول آماده شدند.")


# -----------------------
# دریافت و ذخیره داده‌ها
# -----------------------
def get_and_save_apple_watches(max_pages=2):
    session = SessionLocal()
    all_products = 0
    all_colors = 0

    try:
        for page in range(1, max_pages + 1):
            print(f"\n--- دریافت داده از صفحه {page} ---")
            url = f"{API_URL_BASE}?page={page}"
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            products_list = data.get('data', {}).get('products', [])
            if not products_list:
                print("🛑 لیست محصولات خالی است یا به انتهای صفحات رسیدیم.")
                break

            for prod in products_list:
                product_id = prod.get("id")
                title_fa = prod.get("title_fa")
                relative_url = prod.get("url", {}).get("uri")
                default_variant = prod.get("default_variant")

                selling_price = None
                if isinstance(default_variant, dict):
                    selling_price = default_variant.get("price", {}).get("selling_price")

                if not (product_id and title_fa and relative_url and selling_price):
                    continue

                # بررسی وجود محصول
                db_prod = session.query(WatchProduct).filter_by(product_id=product_id).first()
                if not db_prod:
                    db_prod = WatchProduct(
                        product_id=product_id,
                        title_fa=title_fa,
                        relative_url=f"https://www.digikala.com{relative_url}",
                        selling_price=selling_price
                    )
                    session.add(db_prod)
                else:
                    db_prod.title_fa = title_fa
                    db_prod.relative_url = f"https://www.digikala.com{relative_url}"
                    db_prod.selling_price = selling_price

                # رنگ‌ها
                for color in prod.get("colors", []):
                    color_title = color.get("title")
                    if color_title and color_title not in [c.title for c in db_prod.colors]:
                        db_prod.colors.append(WatchColor(title=color_title))

                all_products += 1
                all_colors += len(db_prod.colors)

            session.commit()
            print(f"✅ صفحه {page} پردازش شد.")

            time.sleep(2)
    except Exception as e:
        session.rollback()
        print(f"❌ خطا در پردازش: {e}")
    finally:
        session.close()

    print(f"\n✨ مجموع محصولات: {all_products} | رنگ‌ها: {all_colors}")


# -----------------------
# نمایش محصولات ذخیره‌شده
# -----------------------
def fetch_saved_products(limit=10):
    session = SessionLocal()
    try:
        products = session.query(WatchProduct).limit(limit).all()
        for i, p in enumerate(products, 1):
            color_list = ", ".join([c.title for c in p.colors]) if p.colors else "ندارد"
            print(f"\n{i}. {p.title_fa}")
            print(f"💰 قیمت: {p.selling_price:,} ریال")
            print(f"🔗 لینک: {p.relative_url}")
            print(f"🎨 رنگ‌ها: {color_list}")
    finally:
        session.close()


# -----------------------
# اجرای Pipeline
# -----------------------
if __name__ == "__main__":
    setup_database()
    get_and_save_apple_watches(max_pages=2)
    fetch_saved_products(limit=5)
