from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Prefer discrete DB_* variables when present (Docker local). Fallback to DATABASE_URL.
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT", "5432")
db_name = os.getenv("DB_NAME")
db_sslmode = os.getenv("DB_SSLMODE")  # e.g., require

if db_user and db_password and db_host and db_name:
    DATABASE_URL = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    if db_sslmode:
        DATABASE_URL += f"?sslmode={db_sslmode}"
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        missing = [k for k, v in {
            "DB_USER": db_user,
            "DB_PASSWORD": db_password,
            "DB_HOST": db_host,
            "DB_NAME": db_name,
        }.items() if not v]

        raise RuntimeError(
            f"Missing required database env vars: {', '.join(missing)}. "
            "Set DB_USER/DB_PASSWORD/DB_HOST/DB_NAME (optional DB_PORT, DB_SSLMODE) or provide DATABASE_URL."
        )

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
