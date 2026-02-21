import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

# Define the path for the database directory
db_dir = 'database'
db_path = os.path.join(db_dir, 'livrables.db')

# Create the database directory if it doesn't exist
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

DATABASE_URL = f"sqlite:///{db_path}"
engine = create_engine(DATABASE_URL)

Base = declarative_base()
