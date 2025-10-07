import requests
import json
import time
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from databases.database import SessionLocal, engine
from models.model import IPHONE_PRODUCTS

DETAILS_API_BASE = "https://api.digikala.com/v2/product/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}


def setup_specs_column():
    """
    بررسی اینکه ستون specifications وجود دارد یا نه.
    اگر در مدل هست ولی در دیتابیس ایجاد نشده، خطایی نمی‌دهد.
    """
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("iphone_products")]
    if "specifications" in columns:
        print("ℹ️ ستون specifications از قبل وجود دارد.")
    else:
        print("⚠️ ستون specifications در دیتابیس وجود ندارد. لطفاً با Alembic یا دستی اضافه‌اش کنید.")


def fetch_and_save_specifications(delay=2):
    """
    دریافت مشخصات فنی برای محصولات آیفون و ذخیره در دیتابیس با استفاده از ORM.
    """
    session: Session = SessionLocal()
    try:
        products = session.query(IPHONE_PRODUCTS).filter(
            (IPHONE_PRODUCTS.specifications == None) | (IPHONE_PRODUCTS.specifications == "")
        ).all()

        print(f"🔍 تعداد محصولات بدون مشخصات: {len(products)}")

        for idx, product in enumerate(products, start=1):
            print(f"\n({idx}/{len(products)}) 🟢 دریافت مشخصات برای محصول {product.product_id} ...")

            url = f"{DETAILS_API_BASE}{product.product_id}/"
            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
                data = response.json()

                specs = data.get("data", {}).get("product", {}).get("specifications", [])
                if not specs:
                    print("⚠️ مشخصاتی یافت نشد.")
                    continue

                specs_json = json.dumps(specs, ensure_ascii=False)
                product.specifications = specs_json
                session.commit()

                print(f"✅ مشخصات برای محصول {product.product_id} ذخیره شد.")

            except requests.exceptions.RequestException as e:
                print(f"❌ خطای درخواست برای {product.product_id}: {e}")
                session.rollback()
                continue
            except Exception as e:
                print(f"❌ خطای دیگر برای {product.product_id}: {e}")
                session.rollback()
                continue

            time.sleep(delay)

    finally:
        session.close()
        print("\n✨ عملیات دریافت مشخصات برای همه محصولات پایان یافت.")


if __name__ == "__main__":
    setup_specs_column()
    fetch_and_save_specifications(delay=2)
