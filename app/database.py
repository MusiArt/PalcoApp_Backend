# app/database.py
from sqlalchemy import create_engine
# ATUALIZADO: Importar declarative_base de sqlalchemy.orm
from sqlalchemy.orm import sessionmaker, declarative_base # MODIFICADO AQUI
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base agora usa a importação atualizada
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()