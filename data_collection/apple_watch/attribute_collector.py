# scripts/watch_specs_orm.py
import requests
import json
import time
from sqlalchemy.orm import Session
from databases.database import SessionLocal
from models.model import WatchProduct

DETAILS_API_BASE = "https://api.digikala.com/v2/product/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json"
}


def fetch_and_save_specifications(delay=2):
    """دریافت مشخصات فنی برای هر محصول و ذخیره به‌صورت JSON در دیتابیس."""
    session: Session = SessionLocal()
    try:
        # گرفتن لیست محصولاتی که هنوز مشخصات ندارند
        products = session.query(WatchProduct).filter(
            (WatchProduct.specifications == None) | (WatchProduct.specifications == "")
        ).all()
        print(f"🔍 تعداد محصولات بدون مشخصات: {len(products)}")

        for idx, product in enumerate(products, start=1):
            url = f"{DETAILS_API_BASE}{product.product_id}/"
            print(f"\n({idx}/{len(products)}) 🟢 دریافت مشخصات برای محصول {product.product_id} ...")

            try:
                response = requests.get(url, headers=HEADERS, timeout=10)
                response.raise_for_status()
                data = response.json()

                # استخراج بخش specifications
                specs = data.get("data", {}).get("product", {}).get("specifications", [])
                if not specs:
                    print("⚠️ مشخصاتی یافت نشد.")
                    continue

                # ذخیره به‌صورت رشته JSON
                specs_json = json.dumps(specs, ensure_ascii=False)
                product.specifications = specs_json

                session.commit()
                print(f"✅ مشخصات برای محصول {product.product_id} ذخیره شد.")

            except requests.exceptions.RequestException as e:
                print(f"❌ خطای درخواست برای {product.product_id}: {e}")
                session.rollback()
            except Exception as e:
                print(f"❌ خطای دیگر برای {product.product_id}: {e}")
                session.rollback()

            # جلوگیری از بلاک شدن
            time.sleep(delay)

    finally:
        session.close()
        print("\n✨ عملیات دریافت مشخصات برای همه محصولات پایان یافت.")


if __name__ == "__main__":
    fetch_and_save_specifications(delay=2)
