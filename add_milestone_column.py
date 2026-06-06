from sqlalchemy import text
from app.models.base import engine

def add_is_milestone_column():
    print("Attempting to add 'is_milestone' column to 'tasks' table...")
    try:
        with engine.connect() as connection:
            connection.execute(text("ALTER TABLE tasks ADD COLUMN is_milestone BOOLEAN NOT NULL DEFAULT FALSE"))
            connection.commit()
        print("'is_milestone' column added successfully.")
    except Exception as e:
        print(f"An error occurred while adding the column: {e}")

if __name__ == "__main__":
    add_is_milestone_column()
