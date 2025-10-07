# ... کدهای قبل از حلقه
import os
import sys
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document  # fix import path for Document

# اضافه کردن مسیر پروژه برای import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from databases.database import SessionLocal
from models.model import IPHONE_PRODUCTS, WATCH_PRODUCTS
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from databases.database import SessionLocal
from models.model import IPHONE_PRODUCTS, WATCH_PRODUCTS

load_dotenv()

# مسیر ذخیره وکتور دیتابیس
VECTOR_DIR = "vectorstore"
FAISS_INDEX_PATH = os.path.join(VECTOR_DIR, "faiss_index")


db = SessionLocal()
# مسیر ذخیره وکتور دیتابیس
VECTOR_DIR = "vectorstore"
FAISS_INDEX_PATH = os.path.join(VECTOR_DIR, "faiss_index")

        # --- گرفتن محصولات ---
iphones = db.query(IPHONE_PRODUCTS).all()
watches = db.query(WATCH_PRODUCTS).all()

if not iphones and not watches:
    print("❌ No products in database.")

documents = []
# --- پردازش آیفون‌ها ---
for p in iphones:
    colors = [c.title for c in p.colors] if p.colors else []
    color_text = ", ".join(colors) if colors else "Unknown"
    specs_text = p.specifications or "Unknown"
    reviews_text = p.reviews_text or "None"
    price_text = f"{p.selling_price:,} تومان" if p.selling_price else "Unknown"

    doc = Document(
        page_content=(
            f"Category: iPhone\n"
            f"Product name: {p.title_fa}\n"
            f"Price: {price_text}\n"
            f"Colors: {color_text}\n"
            f"Specifications: {specs_text}\n"
            f"Reviews: {reviews_text}"
        ),
        metadata={
            "id": p.id,
            "product_id": p.product_id,
            "category": "iphone",
            "url": p.relative_url
        }
    )
    documents.append(doc)

    # پرینت داکیومنت ساخته شده
    print("----- iPhone Document -----")
    print("page_content:")
    print(doc.page_content)
    print("metadata:")
    print(doc.metadata)
    print("---------------------------\n")


# --- پردازش ساعت‌ها ---
for p in watches:
    colors = [c.title for c in p.colors] if p.colors else []
    color_text = ", ".join(colors) if colors else "Unknown"
    specs_text = p.specifications or "Unknown"
    reviews_text = p.reviews_text or "None"
    price_text = f"{p.selling_price:,} تومان" if p.selling_price else "Unknown"

    doc = Document(
        page_content=(
            f"Category: Watch\n"
            f"Product name: {p.title_fa}\n"
            f"Price: {price_text}\n"
            f"Colors: {color_text}\n"
            f"Specifications: {specs_text}\n"
            f"Reviews: {reviews_text}"
        ),
        metadata={
            "id": p.id,
            "Price" : price_text,
            "Colors" : color_text,
            "Specifications" : specs_text,
            "product_id": p.product_id,
            "category": "watch",
            "url": p.relative_url
        }
    )
    documents.append(doc)

    # پرینت داکیومنت ساخته شده
    print("----- Watch Document -----")
    print("page_content:")
    print(doc.page_content)
    print("metadata:")
    print(doc.metadata)
    print("--------------------------\n")
