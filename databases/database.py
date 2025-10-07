# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.model import Base
import os
from dotenv import load_dotenv
load_dotenv()
database = os.getenv("DATABASE_URL")
engine = create_engine(database)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)