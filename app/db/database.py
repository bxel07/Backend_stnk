# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker

# DATABASE_URL = "sqlite:///./app/storage/stnk_data.db"

# engine = create_engine(
#     DATABASE_URL, connect_args={"check_same_thread": False}
# )

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# PostgreSQL Database Configuration
DATABASE_URL = "postgresql://postgres:PMASystemDB2025!@31.97.105.101:5000/stnk_data"

# Alternative format (more explicit)
# DATABASE_URL = "postgresql+psycopg2://postgres:PMASystemDB2025!@31.97.105.101:5000/stnk_data"

engine = create_engine(
    DATABASE_URL,
    # Remove SQLite-specific connect_args
    # connect_args={"check_same_thread": False}  # This is SQLite specific
    pool_pre_ping=True,  # PostgreSQL recommended settings
    pool_recycle=300,
    echo=False  # Set to True for SQL query logging during development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Database dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()