import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

try:
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
except ImportError:
    print("ERROR: config.py not found or is misconfigured.")
    print("Please create a config.py file at the root of the project with DB_HOST, DB_USER, DB_PASSWORD, and DB_NAME.")
    sys.exit(1)

# SQLAlchemy connection string for MySQL with the pymysql driver
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create the engine with connection pooling options suitable for MySQL
engine = create_engine(
    DATABASE_URL,
    pool_recycle=3600,  # Recycle connections every hour to prevent timeouts
    pool_pre_ping=True  # Check connection health before use
)

Base = declarative_base()
