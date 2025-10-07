# api_server.py
# api_server_async.py
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import asyncio
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.agent_creator import creator_tools
from services.manage_sessions import get_or_create_session, load_messages, save_message
from services.rag_service import get_rag_chain

load_dotenv()

app = FastAPI(title="Dastyar AI Chat API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
#  Pydantic
# ----------------------------
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    history: List[dict]

# ----------------------------
# Prompt
# ----------------------------
service_prompt = """
تو یک دستیار هوش مصنوعیهستی که به کاربر کمک می‌کنی محصول مناسب خود را در دیجی‌کالا (گوشی‌های آیفون یا اپل واچ) پیدا کند.
وظیفه تو این است که با پرسیدن سوالات دقیق و گام به گام، محصول موردنظر کاربر را بازیابی کنید و به سوالات خاصی در مورد آن پاسخ بدهی.
...
"""

# ----------------------------
# Agent ,AgentExecutor
# ----------------------------
llm = ChatOpenAI(model=os.getenv("MODEL", "gpt-4o-mini"), temperature=0.7)
prompt = ChatPromptTemplate.from_messages([
    ("system", service_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
tools = creator_tools.copy()
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

# ----------------------------
# Endpoint /chat
# ----------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(data: ChatRequest = Body(...)):
    # session
    session_id = data.session_id or get_or_create_session("api_session")
    chat_history = await asyncio.to_thread(load_messages, session_id) or []

    human_msg = HumanMessage(content=data.message, type="human")
    chat_history.append(human_msg)
    await asyncio.to_thread(save_message, session_id, "human", data.message)

    # Run agent (async)
    response = await agent_executor.ainvoke({
        "input": data.message,
        "chat_history": chat_history
    })
    ai_text = response.get("output") or response.get("result") or str(response)

    # Add AI message to history
    ai_msg = AIMessage(content=ai_text, type="ai")
    chat_history.append(ai_msg)
    await asyncio.to_thread(save_message, session_id, "ai", ai_text)

    history_serializable = [{"type": msg.type, "content": msg.content} for msg in chat_history]

    return ChatResponse(
        session_id=session_id,
        reply=ai_text,
        history=history_serializable
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8001,workers = 4)