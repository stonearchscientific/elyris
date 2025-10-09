from sqlmodel import create_engine, SQLModel, Session
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "elyris.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    from . import models
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
