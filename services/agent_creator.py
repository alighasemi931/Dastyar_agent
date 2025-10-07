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
# 1️⃣ Tool: Filter and extract information from RAG
# -------------------------
class FilterProductsTool(BaseTool):
    name: str = "filter_products"
    description: str = "Apply filters to products retrieved by RAG"

    def _run(self, documents: List[Dict] | str | None = None, color: str = None, min_price: int = None, max_price: int = None, user_query: str = None) -> List[Dict]:
        """
        documents: either a list of dicts or a JSON/string containing the list.
        This method is defensive: the LangChain agent may call tools with a single
        positional input (often a string). We accept None or string and try to
        parse it into the expected list.
        """
        import json

        # If called with no documents, return empty list (nothing to filter)
        if not documents:
            return []

        # If documents is a JSON/string, try to parse
        if isinstance(documents, str):
            try:
                parsed = json.loads(documents)
                # if it was wrapped like {"documents": [...]}
                if isinstance(parsed, dict) and "documents" in parsed:
                    documents = parsed["documents"]
                else:
                    documents = parsed
            except Exception:
                # If parsing fails, we can't filter; return empty list
                return []

        # At this point expect a list of dicts
        results: List[Dict] = []
        # If a natural-language user_query is provided, we can ask the LLM to
        # check whether each product's metadata matches the user's intent.
        # This is useful when the user says things like "رنگ سفید می‌خوام و تا ۳۰ میلیون"
        # and we need to interpret that against the stored metadata.
        use_llm_filter = bool(user_query)

        # Prepare LLM chain once if needed
        if use_llm_filter:
            llm_prompt = """شما یک استخراج‌گر هستید که بررسی می‌کند آیا یک محصول با توضیحات زیر مطابق درخواست کاربر هست یا نه.
ورودی‌ها:
User request: {user_query}
Product info (JSON or متن ساختاری):
{product}

خروجی: دقیقا یکی از کلمه‌های TRUE یا FALSE (بدون متن اضافی). اگر محصول با درخواست کاربر مطابقت دارد TRUE و در غیر این صورت FALSE بنویس.
مثال: TRUE
"""
            llm_chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_template(llm_prompt))

        for doc in documents:
            # If color filter provided, do a simple heuristic match first
            if color:
                doc_colors = [c.lower() for c in doc.get("colors", []) if isinstance(c, str)]
                if isinstance(color, str):
                    if color.lower() not in doc_colors and not any(color.lower() in c for c in doc_colors):
                        continue
                # else: leave as-is

            # If user_query is present, use LLM to vet the product
            if use_llm_filter:
                try:
                    # Build a compact product summary for the LLM
                    product_summary = {
                        "title": doc.get("title") or doc.get("name") or "",
                        "price": doc.get("price"),
                        "colors": doc.get("colors", []),
                        "specs": doc.get("specs") or "",
                        "metadata": doc.get("source") or doc.get("source", {}) or doc.get("source", {})
                    }
                    # If metadata is in a different key, also include full doc metadata
                    if isinstance(doc.get("source"), dict):
                        product_text = str(product_summary)
                    else:
                        # include raw metadata if available
                        product_text = str({**product_summary, **(doc.get("source") or doc.get("metadata") or {})})

                    llm_out = llm_chain.run({"user_query": user_query, "product": product_text})
                    decision = (llm_out or "").strip().upper()
                    if decision and decision.startswith("T"):
                        pass  # keep product
                    else:
                        continue
                except Exception:
                    # On any LLM failure, fall back to heuristics below
                    pass

            price = doc.get("price")
            # price may be a string like '12,000 تومان' — defensive check
            try:
                if isinstance(price, str):
                    # try to extract digits
                    import re
                    digits = re.sub(r"[^0-9]", "", price)
                    price_val = int(digits) if digits else None
                else:
                    price_val = int(price) if price is not None else None
            except Exception:
                price_val = None

            if min_price and (price_val is None or price_val < min_price):
                continue
            if max_price and (price_val is None or price_val > max_price):
                continue
            results.append(doc)
        return results

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("FilterProductsTool does not support async")

# -------------------------
# 2️⃣ Tool: Summarize reviews from RAG
# -------------------------
class SummarizeReviewsTool(BaseTool):
    name: str = "summarize_reviews"
    description: str = "Summarize and analyze up to 20 user reviews from RAG results"

    def _run(self, reviews: list | str, max_reviews: int = 20) -> str:
        """
        Accept either a single large reviews string or a list of review strings.
        Limit to `max_reviews` and produce a short categorized Persian summary.
        """
        if not reviews:
            return "No reviews found."

        if isinstance(reviews, str):
            reviews_list = [r for r in reviews.strip().split("\n") if r.strip()][:max_reviews]
        else:
            reviews_list = [r for r in reviews if isinstance(r, str) and r.strip()][:max_reviews]

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
# 3️⃣ Tool: Compare two products using RAG
# -------------------------
class CompareProductsTool(BaseTool):
    name: str = "compare_products"
    description: str = "Compare two products by price, color, specs and reviews using an LLM"

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
from langchain.tools import BaseTool

class RAGTool(BaseTool):
    name: str = "rag_tool"
    description: str = (
        "Search and retrieve relevant product data using the RAG retriever. "
        "Optionally apply filters such as color and price range before returning results."
    )

    def _run(self, query: str, color: str = None, min_price: int = None, max_price: int = None) -> list:
        """Perform RAG retrieval and apply optional filters before returning results."""
        from services.rag_service import get_vector_retriever
        retriever = get_vector_retriever(k=10)

        if not retriever:
            return "RAG retriever is not available or not initialized."

        docs = retriever.get_relevant_documents(query)
        results = []

        for d in docs:
            text = d.page_content or ""
            title, price, colors, specs, reviews_text = None, None, [], "", ""

            for line in text.splitlines():
                if line.startswith("Product name:"):
                    title = line.replace("Product name:", "").strip()
                elif line.startswith("Price:"):
                    price = line.replace("Price:", "").strip()
                elif line.startswith("Colors:"):
                    colors = [c.strip().lower() for c in line.replace("Colors:", "").split(",") if c.strip()]
                elif line.startswith("Specifications:"):
                    specs = line.replace("Specifications:", "").strip()
                elif line.startswith("Reviews:"):
                    reviews_text = line.replace("Reviews:", "").strip()

            # --- فیلترها ---
            import re
            digits = re.sub(r"[^0-9]", "", price or "")
            price_val = int(digits) if digits else None

            # فیلتر رنگ
            if color and all(color.lower() not in c for c in colors):
                continue
            # فیلتر حداقل قیمت
            if min_price and (not price_val or price_val < min_price):
                continue
            # فیلتر حداکثر قیمت
            if max_price and (not price_val or price_val > max_price):
                continue

            results.append({
                "title": title or d.metadata.get("product_id") or "Unknown",
                "price": price,
                "colors": colors,
                "specs": specs,
                "reviews": reviews_text.split("\n"),
                "source": d.metadata,
            })

        if not results:
            return f"No products found for query '{query}' with the applied filters."

        return results


    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("RAGTool does not support async")

# -------------------------
# Tool list for the Agent
# -------------------------
creator_tools = [
    FilterProductsTool(),
    SummarizeReviewsTool(),
    CompareProductsTool(),
    RAGTool(),
]


# -------------------------
# 5️⃣ Tool: Categorize products based on review summaries
# -------------------------
class CategorizeProductsTool(BaseTool):
    name: str = "categorize_products"
    description: str = "Given a list of products (with reviews), categorize them by review-derived topics and return a short Persian summary per category."

    def _run(self, products: list) -> dict:
        if not products:
            return {}

        # Build a prompt that provides up to 20 reviews per product and asks the LLM to group products
        items_text = []
        for p in products:
            reviews = p.get("reviews") or []
            reviews_text = "\n".join(reviews[:20])
            items_text.append(f"Product: {p.get('title')}\nReviews:\n{reviews_text}\n---")

        prompt = """شما یک تحلیل‌گر خرید حرفه‌ای هستید.
با استفاده از اطلاعات محصولات و بررسی‌های کاربران، محصولات را بر اساس موضوعات مهم (مثلاً: کیفیت ساخت، عمر باتری، ارزش در مقابل قیمت، طراحی) دسته‌بندی کن.
برای هر دسته، فهرستی از محصولات مرتبط و یک خلاصه کوتاه پاراگرافی به فارسی بنویس.

ورودی:
{items}

خروجی:""".replace("{items}", "\n\n".join(items_text))

        chain = LLMChain(llm=llm, prompt=ChatPromptTemplate.from_template(prompt))
        output = chain.run({})
        # Return raw LLM output (string) which will contain categorized groups
        return {"categories_summary": output}


# expose extended tools
creator_tools.append(CategorizeProductsTool())
