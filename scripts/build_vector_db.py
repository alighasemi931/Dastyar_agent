# scripts/build_vector_db.py
import os
import sys
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document  # اصلاح مسیر Document
from dotenv import load_dotenv
# اضافه کردن مسیر پروژه
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from databases.database import SessionLocal
from models.model import IPHONE_PRODUCTS, WATCH_PRODUCTS, IPHONE_COLORS, WATCH_COLORS
load_dotenv()
# مسیر ذخیره‌سازی وکتور دیتابیس
CHROMA_DIR = "vectorstore"

def build_vector_db():
    db = SessionLocal()
    try:
        # --- دریافت همه محصولات آیفون و ساعت ---
        iphones = db.query(IPHONE_PRODUCTS).all()
        watches = db.query(WATCH_PRODUCTS).all()

        if not iphones and not watches:
            print("❌ هیچ محصولی در دیتابیس وجود ندارد.")
            return

        documents = []

        # --- پردازش آیفون‌ها ---
        for p in iphones:
            colors = [c.title for c in p.colors] if p.colors else []
            color_text = ", ".join(colors) if colors else "نامشخص"
            specs_text = p.specifications or "نامشخص"
            reviews_text = p.reviews_text or "ندارد"
            price_text = f"{p.selling_price:,} تومان" if p.selling_price else "نامشخص"

            doc = Document(
                page_content=(
                    f"دسته‌بندی: آیفون\n"
                    f"نام محصول: {p.title_fa}\n"
                    f"قیمت: {price_text}\n"
                    f"رنگ‌ها: {color_text}\n"
                    f"مشخصات: {specs_text}\n"
                    f"نقد و بررسی: {reviews_text}"
                ),
                metadata={
                    "id": p.id,
                    "product_id": p.product_id,
                    "category": "iphone",
                    "url": p.relative_url
                }
            )
            documents.append(doc)

        # --- پردازش ساعت‌ها ---
        for p in watches:
            colors = [c.title for c in p.colors] if p.colors else []
            color_text = ", ".join(colors) if colors else "نامشخص"
            specs_text = p.specifications or "نامشخص"
            reviews_text = p.reviews_text or "ندارد"
            price_text = f"{p.selling_price:,} تومان" if p.selling_price else "نامشخص"

            doc = Document(
                page_content=(
                    f"دسته‌بندی: ساعت\n"
                    f"نام محصول: {p.title_fa}\n"
                    f"قیمت: {price_text}\n"
                    f"رنگ‌ها: {color_text}\n"
                    f"مشخصات: {specs_text}\n"
                    f"نقد و بررسی: {reviews_text}"
                ),
                metadata={
                    "id": p.id,
                    "product_id": p.product_id,
                    "category": "watch",
                    "url": p.relative_url
                }
            )
            documents.append(doc)

        # --- ایجاد مدل برداری ---
        embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))

        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=CHROMA_DIR
        )

        vector_store.persist()
        print(f"✅ وکتور دیتابیس با موفقیت ساخته شد و در مسیر '{CHROMA_DIR}' ذخیره شد.")
        print(f"📦 تعداد مستندات: {len(documents)}")

    except Exception as e:
        print(f"❌ خطا در ساخت وکتور دیتابیس: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    build_vector_db()
