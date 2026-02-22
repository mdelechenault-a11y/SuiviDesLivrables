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
    Synchronizes the database schema. Creates tables and adds missing columns
    for a simple development workflow.
    NOTE: This is a basic migration helper, not a replacement for a full
    migration tool like Alembic in production.
    """
    print("Attempting to synchronize database schema...")
    try:
        # The create_all function checks for the existence of tables before creating them.
        Base.metadata.create_all(engine)
        print("Database synchronization complete. All tables should now exist.")

        # --- Simple migration for missing columns ---
        inspector = inspect(engine)
        all_tables = inspector.get_table_names()

        with engine.connect() as connection:
            if 'livrables' in all_tables:
                livrables_cols = [c['name'] for c in inspector.get_columns('livrables')]
                migrations_to_apply = {
                    'date_initiale': 'ALTER TABLE livrables ADD COLUMN date_initiale DATE',
                    'responsabilite_retard': 'ALTER TABLE livrables ADD COLUMN responsabilite_retard VARCHAR'
                }
                for col, statement in migrations_to_apply.items():
                    if col not in livrables_cols:
                        print(f"Applying migration: Adding '{col}' to 'livrables' table...")
                        with connection.begin():
                            connection.execute(text(statement))
                        print(f"'{col}' column added successfully.")

            if 'clients' in all_tables:
                clients_cols = [c['name'] for c in inspector.get_columns('clients')]
                migrations_to_apply = {
                    'code': 'ALTER TABLE clients ADD COLUMN code VARCHAR(3)',
                    'address': 'ALTER TABLE clients ADD COLUMN address TEXT',
                    'phone': 'ALTER TABLE clients ADD COLUMN phone VARCHAR',
                    'website': 'ALTER TABLE clients ADD COLUMN website VARCHAR'
                }
                for col, statement in migrations_to_apply.items():
                    if col not in clients_cols:
                        print(f"Applying migration: Adding '{col}' to 'clients' table...")
                        with connection.begin():
                            connection.execute(text(statement))
                        print(f"'{col}' column added successfully.")

            if 'users' in all_tables:
                users_cols = [c['name'] for c in inspector.get_columns('users')]
                if 'company_id' not in users_cols:
                    print("Applying migration: Adding 'company_id' to 'users' table...")
                    with connection.begin():
                        connection.execute(text('ALTER TABLE users ADD COLUMN company_id INTEGER REFERENCES companies(id)'))
                    print("'company_id' column added to 'users' successfully.")

            if 'projects' in all_tables:
                projects_cols = [c['name'] for c in inspector.get_columns('projects')]
                if 'company_id' not in projects_cols:
                    print("Applying migration: Adding 'company_id' to 'projects' table...")
                    with connection.begin():
                        connection.execute(text('ALTER TABLE projects ADD COLUMN company_id INTEGER REFERENCES companies(id)'))
                    print("'company_id' column added to 'projects' successfully.")
            
            if 'companies' in all_tables:
                companies_cols = [c['name'] for c in inspector.get_columns('companies')]
                migrations_to_apply = {
                    'objective_point_mort': 'ALTER TABLE companies ADD COLUMN objective_point_mort FLOAT DEFAULT 0.0',
                    'objective_1': 'ALTER TABLE companies ADD COLUMN objective_1 FLOAT DEFAULT 0.0',
                    'objective_2': 'ALTER TABLE companies ADD COLUMN objective_2 FLOAT DEFAULT 0.0'
                }
                for col, statement in migrations_to_apply.items():
                    if col not in companies_cols:
                        print(f"Applying migration: Adding '{col}' to 'companies' table...")
                        with connection.begin():
                            connection.execute(text(statement))
                        print(f"'{col}' column added successfully.")

    except Exception as e:
        print(f"An error occurred during database synchronization: {e}")

if __name__ == "__main__":
    synchronize_database()
