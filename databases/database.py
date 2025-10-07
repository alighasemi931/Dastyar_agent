# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.model import Base
import os
from dotenv import load_dotenv

load_dotenv()

# Read DATABASE_URL from environment; if missing, fall back to a local sqlite file
database = os.getenv("DATABASE_URL")
if not database:
    # Use a file next to the repository for easy local development
    fallback_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dastyar.db")
    database = f"sqlite:///{fallback_path}"
    print("WARNING: DATABASE_URL not set. Falling back to sqlite database at:", fallback_path)

# For sqlite we must pass check_same_thread; otherwise leave connect_args empty
connect_args = {"check_same_thread": False} if database.startswith("sqlite") else {}

engine = create_engine(database, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)