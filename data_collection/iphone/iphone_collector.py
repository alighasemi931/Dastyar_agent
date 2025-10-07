# scripts/digikala_orm.py
import requests
import time
from sqlalchemy import Column, Integer, String, Text, ForeignKey, create_engine
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# --- تنظیمات ---
DB_NAME = "sqlite:///digikala_products.db"
API_URL_BASE = "https://api.digikala.com/v1/categories/mobile-phone/brands/apple/search/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36',
    'Accept': 'application/json'
}

Base = declarative_base()

# -----------------------
#  مدل‌ها (ORM)
# -----------------------
class IPhoneProduct(Base):
    __tablename__ = "iphone_products"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True)
    title_fa = Column(Text)
    relative_url = Column(Text)
    selling_price = Column(Integer)

    colors = relationship("IPhoneColor", back_populates="product", cascade="all, delete-orphan")


class IPhoneColor(Base):
    __tablename__ = "iphone_colors"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("iphone_products.product_id"))
    title = Column(Text)

    product = relationship("IPhoneProduct", back_populates="colors")


# -----------------------
#  راه‌اندازی دیتابیس
# -----------------------
engine = create_engine(DB_NAME)
SessionLocal = sessionmaker(bind=engine)

def setup_database():
    Base.metadata.create_all(engine)
    print(f"✅ دیتابیس و جداول ORM آماده شدند.")


# -----------------------
#  دریافت و ذخیره داده‌ها
# -----------------------
def get_and_save_apple_mobiles(max_pages=5):
    session = SessionLocal()
    total_products = 0
    total_colors = 0

    try:
        for page in range(1, max_pages + 1):
            print(f"\n--- دریافت داده از صفحه {page} ---")
            url = f"{API_URL_BASE}?page={page}"

            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
            products_list = data.get("data", {}).get("products", [])

            if not products_list:
                print("🛑 لیست محصولات خالی است یا به انتهای صفحات رسیدیم.")
                break

            for product in products_list:
                product_id = product.get("id")
                title_fa = product.get("title_fa")
                relative_url = product.get("url", {}).get("uri")
                selling_price = None

                default_variant = product.get("default_variant")
                if isinstance(default_variant, dict):
                    price_info = default_variant.get("price", {})
                    selling_price = price_info.get("selling_price")
                elif isinstance(default_variant, list) and len(default_variant) > 0:
                    price_info = default_variant[0].get("price", {})
                    selling_price = price_info.get("selling_price")

                if not (product_id and title_fa and relative_url and selling_price):
                    continue

                # بررسی وجود محصول (برای به‌روزرسانی یا ایجاد)
                db_product = session.query(IPhoneProduct).filter_by(product_id=product_id).first()
                if not db_product:
                    db_product = IPhoneProduct(
                        product_id=product_id,
                        title_fa=title_fa,
                        relative_url=f"https://www.digikala.com{relative_url}",
                        selling_price=selling_price
                    )
                    session.add(db_product)
                else:
                    db_product.title_fa = title_fa
                    db_product.relative_url = f"https://www.digikala.com{relative_url}"
                    db_product.selling_price = selling_price

                # رنگ‌ها
                colors = product.get("colors", [])
                for color in colors:
                    color_title = color.get("title")
                    if color_title and color_title not in [c.title for c in db_product.colors]:
                        db_product.colors.append(IPhoneColor(title=color_title))

                total_products += 1
                total_colors += len(colors)

            session.commit()
            print(f"✅ صفحه {page}: {len(products_list)} محصول پردازش شد.")
            time.sleep(2)

    except Exception as e:
        print(f"❌ خطا در پردازش داده‌ها: {e}")
        session.rollback()
    finally:
        session.close()

    print(f"\n✨ عملیات پایان یافت. مجموع محصولات: {total_products} | مجموع رنگ‌ها: {total_colors}")


# -----------------------
#  نمایش داده‌های ذخیره‌شده
# -----------------------
def fetch_saved_products_with_colors(limit=10):
    session = SessionLocal()
    try:
        products = session.query(IPhoneProduct).limit(limit).all()
        for i, p in enumerate(products, start=1):
            color_list = ", ".join([c.title for c in p.colors]) if p.colors else "فاقد اطلاعات رنگ"
            print(f"\n{i}. {p.title_fa}")
            print(f"   قیمت: {p.selling_price:,} ریال")
            print(f"   رنگ‌ها: {color_list}")
            print(f"   لینک: {p.relative_url}")
    finally:
        session.close()


# -----------------------
#  اجرای Pipeline
# -----------------------
if __name__ == "__main__":
    setup_database()
    get_and_save_apple_mobiles(max_pages=5)
    fetch_saved_products_with_colors(limit=10)
