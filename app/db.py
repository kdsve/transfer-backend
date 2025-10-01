from sqlmodel import SQLModel, create_engine, Session
from .config import settings

db_url = settings.DATABASE_URL
# Render иногда выдаёт postgres:// — меняем на новую схему драйвера
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url, pool_pre_ping=True)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
