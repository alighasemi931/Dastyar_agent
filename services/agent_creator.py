# services/creator_tools.py
import os
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import LLMChain
from langchain.tools import BaseTool
from databases.database import SessionLocal
from models.model import IPHONE_PRODUCTS, WATCH_PRODUCTS
from services.rag_service import get_rag_chain
from dotenv import load_dotenv

load_dotenv()

# -------------------------
# LLM
# -------------------------
LLM_MODEL = os.getenv("MODEL", "gpt-4o-mini")
llm = ChatOpenAI(model=LLM_MODEL, temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

# -------------------------
# 1️⃣ Tool: فیلتر و استخراج اطلاعات روی RAG
# -------------------------
class FilterProductsTool(BaseTool):
    name: str = "filter_products"
    description: str = "اعمال فیلتر روی محصولات استخراج شده توسط RAG"

    def _run(self, documents: List[Dict], color: str = None, min_price: int = None, max_price: int = None) -> List[Dict]:
        results = []
        for doc in documents:
            if color and color not in doc.get("colors", []):
                continue
            price = doc.get("price")
            if min_price and price < min_price:
                continue
            if max_price and price > max_price:
                continue
            results.append(doc)
        return results

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("FilterProductsTool does not support async")

# -------------------------
# 2️⃣ Tool: خلاصه نظرات روی RAG
# -------------------------
class SummarizeReviewsTool(BaseTool):
    name: str = "summarize_reviews"
    description: str = "خلاصه و تحلیل حداکثر 20 نظر کاربران روی نتایج RAG"

    def _run(self, reviews_text: str, max_reviews: int = 20) -> str:
        if not reviews_text:
            return "بدون نظر ثبت شده."
        reviews_list = [r for r in reviews_text.strip().split("\n") if r.strip()][:max_reviews]

        prompt_template = """شما یک تحلیل‌گر حرفه‌ای هستید.
با استفاده از نظرات زیر کاربران در مورد یک محصول اپل، یک خلاصه کوتاه و دسته‌بندی‌شده ایجاد کنید
(مثلاً قیمت، کیفیت، زیبایی) و در قالب پاراگراف به زبان فارسی ارائه دهید.

نظرات کاربران:
{reviews}

خلاصه:"""

        chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_template(prompt_template))
        return chain.run({"reviews": "\n".join(reviews_list)})

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("SummarizeReviewsTool does not support async")

# -------------------------
# 3️⃣ Tool: مقایسه دو محصول روی RAG
# -------------------------
class CompareProductsTool(BaseTool):
    name: str = "compare_products"
    description: str = "مقایسه دو محصول از نظر قیمت، رنگ، مشخصات و نظرات با LLM"

    def _run(self, product_a: Dict, product_b: Dict) -> str:
        prompt_template = """شما یک دستیار مقایسه حرفه‌ای هستید.
دو محصول با مشخصات زیر داده شده‌اند.
یک مقایسه دقیق و خوانا بین دو محصول انجام بده و روی قیمت، رنگ، کیفیت و مشخصات تمرکز کن.
همچنین خلاصه‌ای از نظرات کاربران ارائه کن و نتیجه را به صورت پاراگراف فارسی بنویس.

محصول اول:
نام: {title_a}
قیمت: {price_a}
رنگ‌ها: {colors_a}
مشخصات: {specs_a}
نظرات: {reviews_a}

محصول دوم:
نام: {title_b}
قیمت: {price_b}
رنگ‌ها: {colors_b}
مشخصات: {specs_b}
نظرات: {reviews_b}

مقایسه:"""

        chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_template(prompt_template))
        return chain.run({
            "title_a": product_a["title"],
            "price_a": product_a["price"],
            "colors_a": ", ".join(product_a.get("colors", [])),
            "specs_a": product_a.get("specs") or "",
            "reviews_a": product_a.get("reviews") or "",

            "title_b": product_b["title"],
            "price_b": product_b["price"],
            "colors_b": ", ".join(product_b.get("colors", [])),
            "specs_b": product_b.get("specs") or "",
            "reviews_b": product_b.get("reviews") or "",
        })

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("CompareProductsTool does not support async")

# -------------------------
# 4️⃣ Tool: RAG Tool
# -------------------------
class RAGTool(BaseTool):
    name: str = "rag_tool"
    description: str = "جستجوی محصول با RAG و پاسخ به سوالات کاربر با توجه به وکتور دیتابیس"

    def _run(self, query: str) -> str:
        rag_chain = get_rag_chain()
        if not rag_chain:
            return "ابزار RAG آماده نیست."

        # ⚡ استفاده از invoke به جای فراخوانی مستقیم
        rag_output = rag_chain.invoke({"input": query})

        # اگر خروجی JSON باشد
        try:
            import json
            documents = json.loads(rag_output) if isinstance(rag_output, str) else rag_output
        except Exception:
            documents = [{"title": rag_output, "price": None, "colors": [], "specs": "", "reviews": ""}]

        return str(documents)

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("RAGTool does not support async")

# -------------------------
# لیست ابزارها برای Agent
# -------------------------
creator_tools = [
    FilterProductsTool(),
    SummarizeReviewsTool(),
    CompareProductsTool(),
    RAGTool()
]
