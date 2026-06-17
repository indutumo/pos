from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Replace with actual DB URL or use .env
DATABASE_URL = "postgresql://postgres:gachuhiisaac@localhost/pos_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
