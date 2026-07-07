from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLACHEMY_DATABASE_URL = "sqlite:///./blog.db"

engine = create_engine(
    SQLACHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
    
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as db:
        yield db
        