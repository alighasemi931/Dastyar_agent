from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List

Base = declarative_base()

# -----------------------------
# SQLAlchemy Models
# -----------------------------

class IPHONE_PRODUCTS(Base):
    __tablename__ = 'iphones'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True)
    title_fa = Column(String)
    relative_url = Column(Text)
    selling_price = Column(Integer)
    specifications = Column(Text)
    reviews_text = Column(Text)

    colors = relationship("IPHONE_COLORS", back_populates="iphone", cascade="all, delete-orphan")


class WATCH_PRODUCTS(Base):
    __tablename__ = 'watches'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, unique=True, index=True)
    title_fa = Column(String)
    relative_url = Column(Text)
    selling_price = Column(Integer)
    specifications = Column(Text)
    reviews_text = Column(Text)

    colors = relationship("WATCH_COLORS", back_populates="watch", cascade="all, delete-orphan")


class IPHONE_COLORS(Base):
    __tablename__ = 'iphone_colors'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("iphones.product_id"), index=True)
    title = Column(Text)

    iphone = relationship("IPHONE_PRODUCTS", back_populates="colors")


class WATCH_COLORS(Base):
    __tablename__ = 'watch_colors'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("watches.product_id"), index=True)
    title = Column(Text)

    watch = relationship("WATCH_PRODUCTS", back_populates="colors")


class Session(Base):
    __tablename__ = 'sessions'
    id = Column(Integer, primary_key=True)
    mode = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('sessions.id'), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")


# -----------------------------
# Pydantic Models
# -----------------------------

class SkillData(BaseModel):
    name: str


class ProfileData(BaseModel):
    full_name: str
    headline: str
    summary: str
    skills: List[SkillData]

    model_config = ConfigDict(from_attributes=True)


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.session_id"))
    sender_type = Column(String)  # 'human' or 'ai'
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")
