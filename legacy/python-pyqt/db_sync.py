# db_sync.py
import sys
import os

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import inspect, text
from app.models.base import Base, engine
from app.models.schema import Livrable, Profil, TaskAssignment, User, Client, Project, ActivityType, Task, TimeEntry, LivrableComment, Company

def synchronize_database():
    """
    Ensures that all tables defined in the SQLAlchemy models exist in the database.
    This function is idempotent and safe to run on every application startup.
    """
    print("Attempting to synchronize database schema...")
    try:
        # The create_all function checks for the existence of tables before creating them.
        Base.metadata.create_all(engine)
        print("Database synchronization complete. All tables should now exist.")
    except Exception as e:
        print(f"An error occurred during database synchronization: {e}")

if __name__ == "__main__":
    synchronize_database()
