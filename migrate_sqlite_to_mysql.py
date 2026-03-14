# migrate_sqlite_to_mysql.py
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Base and all models to ensure they are registered with SQLAlchemy's metadata
from app.models.base import Base
from app.models.schema import (
    Company, Profil, Client, User, Project, ActivityType, Task, Livrable,
    LivrableComment, TaskAssignment, TimeEntry
)

def migrate_data():
    """
    Migrates data from an existing SQLite database to a new MySQL database.
    This script first ensures all tables exist in the target DB, then deletes
    all existing data before migrating.
    """
    print("--- Starting Data Migration from SQLite to MySQL ---")

    # --- 1. Setup Database Connections ---
    # Source: SQLite
    sqlite_db_path = os.path.join(project_root, 'database', 'livrables.db')
    if not os.path.exists(sqlite_db_path):
        print(f"ERROR: SQLite database not found at '{sqlite_db_path}'")
        return

    sqlite_url = f"sqlite:///{sqlite_db_path}"
    sqlite_engine = create_engine(sqlite_url)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    print(f"Connected to source SQLite DB: {sqlite_db_path}")

    # Target: MySQL (from config)
    try:
        from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
        mysql_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
        mysql_engine = create_engine(mysql_url)
        # Test connection
        with mysql_engine.connect() as connection:
            print(f"Connected to target MySQL DB: {DB_NAME} on {DB_HOST}")
        MysqlSession = sessionmaker(bind=mysql_engine)
    except ImportError:
        print("ERROR: config.py not found. Please create it with your MySQL credentials.")
        return
    except Exception as e:
        print(f"ERROR: Could not connect to MySQL database. Please check your config.py and server status.")
        print(f"Details: {e}")
        return

    # --- 2. Create Schema and Get Models ---
    print("\nEnsuring all tables exist in the target MySQL database...")
    Base.metadata.create_all(mysql_engine)
    print("Target schema is up to date.")

    # SQLAlchemy's metadata stores tables in dependency-sorted order
    tables_in_order = Base.metadata.sorted_tables

    # Create a mapping from table name to model class for efficient lookup
    class_map = {mapper.local_table.name: mapper.class_ for mapper in Base.registry.mappers}

    sqlite_session = SqliteSession()
    mysql_session = MysqlSession()

    # --- 3. Perform Migration ---
    try:
        print("\nWARNING: All data in the target MySQL tables will be deleted.")
        confirm = input("Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Migration aborted by user.")
            return

        print("\nDisabling foreign key checks on MySQL...")
        with mysql_session.begin():
            mysql_session.execute(text("SET FOREIGN_KEY_CHECKS=0;"))

        # Migrate tables in reverse order for deletion, then forward order for insertion
        with mysql_session.begin():
            for table in reversed(tables_in_order):
                if table.name not in class_map:
                    print(f"  Skipping table '{table.name}' as it has no corresponding model.")
                    continue
                model_class = class_map[table.name]
                print(f"Deleting existing data from {model_class.__tablename__}...")
                mysql_session.query(model_class).delete(synchronize_session=False)
            print("All target tables cleared.")

            for table in tables_in_order:
                if table.name not in class_map:
                    continue
                model_class = class_map[table.name]
                print(f"Migrating data for {model_class.__tablename__}...")

                items = sqlite_session.query(model_class).all()
                if not items:
                    print(f"  No data to migrate for {model_class.__tablename__}.")
                    continue

                data_to_insert = [{c.name: getattr(item, c.name) for c in item.__table__.columns} for item in items]

                if data_to_insert:
                    mysql_session.bulk_insert_mappings(model_class, data_to_insert)
                    print(f"  Successfully migrated {len(data_to_insert)} rows.")

        print("\n--- Migration Completed Successfully! ---")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED: {e}")
        print("Rolling back changes...")
        # The 'with mysql_session.begin()' block handles rollback automatically on error.
    finally:
        print("\nRe-enabling foreign key checks on MySQL...")
        with mysql_session.begin():
            mysql_session.execute(text("SET FOREIGN_KEY_CHECKS=1;"))

        sqlite_session.close()
        mysql_session.close()
        print("Database sessions closed.")

if __name__ == "__main__":
    migrate_data()