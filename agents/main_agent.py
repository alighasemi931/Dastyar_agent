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


# اضافه کردن مسیر سرویس‌ها
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.agent_creator import creator_tools
from services.manage_sessions import get_or_create_session, load_messages, save_message 
from services.rag_service import get_rag_chain

load_dotenv()

# ----------------------------
# Prompt اصلی برای سیستم
# ----------------------------
service_prompt = """
تو یک دستیار هوش مصنوعیهستی که به کاربر کمک می‌کنی محصول مناسب خود را در دیجی‌کالا (گوشی‌های آیفون یا اپل واچ) پیدا کند.
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
# تابع اصلی اجرای Agent
# ----------------------------
def run_creator_mode():
    session_id = get_or_create_session("creator")
    
    # بارگذاری RAG chain
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
    
    # ایجاد agent ترکیبی: ابزارها + RAG
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
    
    # نمایش پیام‌های قبلی
    for msg in st.session_state.creator_messages:
        st.chat_message(msg.type).write(msg.content)
    
    # دریافت ورودی از کاربر
    if user_input := st.chat_input("پاسخ شما..."):
        human_msg = HumanMessage(content=user_input, type="human")
        st.session_state.creator_messages.append(human_msg)
        save_message(session_id, "human", user_input)
        st.chat_message("human").write(user_input)
        
        with st.spinner("Agent در حال پردازش..."):
            # اجرای agent با chat_history
            response = agent_executor.invoke({
                "input": user_input,
                "chat_history": st.session_state.creator_messages
            })
        
        ai_text = response.get("output") or response.get("result") or str(response)
        ai_msg = AIMessage(content=ai_text, type="ai")
        st.session_state.creator_messages.append(ai_msg)
        save_message(session_id, "ai", ai_text)
        st.chat_message("ai").write(ai_text)


if __name__ == "__main__":
    run_creator_mode()