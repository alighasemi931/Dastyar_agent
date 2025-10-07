# 
# services/session_orm.py
import uuid
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from langchain_core.messages import HumanMessage, AIMessage
from models.model import Session , Message
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """ایجاد جداول دیتابیس (در صورت عدم وجود)."""
    Base.metadata.create_all(bind=engine)


def get_or_create_session(user_context='creator') -> str:
    """ساخت یا بازیابی یک Session جدید."""
    db = SessionLocal()
    session_id = str(uuid.uuid4())

    session_obj = Session(session_id=session_id)
    db.add(session_obj)
    db.commit()
    db.close()
    return session_id


def save_message(session_id: str, sender_type: str, content: str):
    """ذخیره یک پیام جدید."""
    db = SessionLocal()
    try:
        message = Message(session_id=session_id, sender_type=sender_type, content=content)
        db.add(message)
        db.commit()
    except Exception as e:
        print(f"❌ خطای ذخیره پیام: {e}")
        db.rollback()
    finally:
        db.close()


def load_messages(session_id: str, limit: int = 10):
    """بارگذاری پیام‌ها برای بازسازی تاریخچه چت (آخرین n پیام)."""
    db = SessionLocal()
    messages = []
    try:
        query = db.query(Message).filter(Message.session_id == session_id)\
                                 .order_by(Message.timestamp.asc())\
                                 .limit(limit)
        for msg in query.all():
            if msg.sender_type == 'human':
                messages.append(HumanMessage(content=msg.content))
            elif msg.sender_type == 'ai':
                messages.append(AIMessage(content=msg.content))
    finally:
        db.close()
    return messages


# -------------------------
# اجرای اولیه
# -------------------------
init_db()