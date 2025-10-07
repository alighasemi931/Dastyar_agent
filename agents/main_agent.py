# main_agent.py
import streamlit as st
import os
from dotenv import load_dotenv
import sys
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool


# add services path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.agent_creator import creator_tools, SummarizeReviewsTool, CategorizeProductsTool
from services.manage_sessions import get_or_create_session, load_messages, save_message 
from services.rag_service import get_rag_chain

load_dotenv()

# ----------------------------
# main system prompt
# ----------------------------
service_prompt = """
تو یک دستیار هوش مصنوعی هستی که به کاربر کمک می‌کنی محصول مناسب خود را در دیجی‌کالا (گوشی‌های آیفون یا اپل واچ) پیدا کند.
وظیفه تو این است که با پرسیدن سوالات دقیق و گام به گام، محصول موردنظر کاربر را بازیابی کنید و به سوالات خاصی در مورد آن پاسخ بدهی.

قوانین:
1. در هر لحظه فقط یک سوال بپرس و مکالمه را فعالانه هدایت کن.
2. با پرسیدن محصول مورد نظر ('آیفون' یا 'اپل واچ') شروع کن.
3. مکالمه را به طور فعال هدایت کنید.
4. پس از تأیید محصول، از کاربر بخواه فیلترهای مورد نظرش (مثل رنگ یا محدوده قیمت) را اعلام کند.
5. از کاربر بپرس که آیا نیاز به دانستن نظرات کاربران دارد یا خیر.
6. از کاربر بپرس که آیا نیاز به مقایسه بین دو محصول را با استفاده از نظرات دارد یا خیر.
7. از ابزارهای موجود (Tools) برای جستجوی داده‌ها و ارائه نتایج استفاده کن.
8. نتایج را به صورت شفاف و کاربرپسند ارائه بده.
"""


# ----------------------------
# main Agent run function
# ----------------------------
def run_creator_mode():
    session_id = get_or_create_session("creator")
    
    # load RAG chain
    rag_chain = get_rag_chain()
    
    # LLM
    llm = ChatOpenAI(model=os.getenv("MODEL", "gpt-4o-mini"), temperature=0.7)
    
    # Prompt agent
    prompt = ChatPromptTemplate.from_messages([
        ("system", service_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # create composite agent: tools + RAG
    tools = creator_tools.copy()
    
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # initialize chat messages
    if "creator_messages" not in st.session_state:
        st.session_state.creator_messages = load_messages(session_id) or []
        if not st.session_state.creator_messages:
            initial_msg = "سلام! لطفاً بگویید که محصول مورد نظر شما چیست؟ (آیفون یا اپل واچ)"
            ai_msg = AIMessage(content=initial_msg, type="ai")
            st.session_state.creator_messages.append(ai_msg)
            save_message(session_id, "ai", initial_msg)
    
    # show previous messages
    for msg in st.session_state.creator_messages:
        st.chat_message(msg.type).write(msg.content)
    
    # get input from user
    if user_input := st.chat_input("پاسخ شما..."):
        human_msg = HumanMessage(content=user_input, type="human")
        st.session_state.creator_messages.append(human_msg)
        save_message(session_id, "human", user_input)
        st.chat_message("human").write(user_input)
        
        def _prepare_chat_history(messages, keep_last: int = 12, max_msg_len: int = 2000):
            """Return a trimmed copy of messages: keep only the last `keep_last` messages.
            Also truncate any very long message.content to `max_msg_len` characters.
            """
            if not messages:
                return []

            # take last N messages
            trimmed = messages[-keep_last:]

            # create shallow copies with truncated content to avoid modifying session state
            out = []
            for m in trimmed:
                try:
                    content = getattr(m, "content", str(m)) or ""
                except Exception:
                    content = str(m)

                if len(content) > max_msg_len:
                    content = content[:max_msg_len] + "\n\n...متن کوتاه شد (بخش طولانی حذف شد)"

                # Preserve message type by recreating minimal message objects
                if getattr(m, "type", None) == "human":
                    out.append(HumanMessage(content=content, type="human"))
                elif getattr(m, "type", None) == "ai":
                    out.append(AIMessage(content=content, type="ai"))
                else:
                    # fallback: keep as HumanMessage
                    out.append(HumanMessage(content=content, type="human"))

            return out

        with st.spinner("Agent در حال پردازش..."):
            # run agent with a trimmed chat_history to avoid exceeding model context length
            safe_history = _prepare_chat_history(st.session_state.creator_messages, keep_last=12, max_msg_len=2000)
            response = agent_executor.invoke({
                "input": user_input,
                "chat_history": safe_history
            })
        
        raw_output = response.get("output") or response.get("result") or response

        # If tools returned structured data (e.g., RAGTool returns list of product dicts),
        # create human-readable summaries for display.
        ai_text = None
        try:
            # Case: list of products
            if isinstance(raw_output, list):
                summarizer = SummarizeReviewsTool()
                categorizer = CategorizeProductsTool()

                lines = []
                for idx, p in enumerate(raw_output, start=1):
                    title = p.get("title") or "Unknown"
                    price = p.get("price") or "Unknown"
                    colors = ", ".join(p.get("colors", [])) if p.get("colors") else "-"
                    specs = p.get("specs") or "-"
                    reviews = p.get("reviews") or []

                    # generate a short categorized summary for up to 20 reviews
                    try:
                        review_summary = summarizer._run(reviews, max_reviews=20)
                    except Exception:
                        review_summary = "خلاصه نظرات در دسترس نیست."

                    lines.append(f"{idx}. {title}\nقیمت: {price}\nرنگ‌ها: {colors}\nمشخصات: {specs}\nخلاصه نظرات: {review_summary}\n")

                # Also produce category-level grouping based on reviews
                try:
                    categories = categorizer._run(raw_output)
                    cat_text = categories.get("categories_summary") if isinstance(categories, dict) else str(categories)
                    lines.append("دسته‌بندی کلی:\n" + str(cat_text))
                except Exception:
                    # if categorization fails, ignore
                    pass

                ai_text = "\n\n".join(lines)

            # Case: dict -> pretty print
            elif isinstance(raw_output, dict):
                import json
                ai_text = json.dumps(raw_output, ensure_ascii=False, indent=2)

            else:
                ai_text = str(raw_output)
        except Exception:
            ai_text = str(raw_output)
        ai_msg = AIMessage(content=ai_text, type="ai")
        st.session_state.creator_messages.append(ai_msg)
        save_message(session_id, "ai", ai_text)
        st.chat_message("ai").write(ai_text)


if __name__ == "__main__":
    run_creator_mode()