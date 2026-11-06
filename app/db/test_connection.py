from sqlalchemy import text
from app.db.database import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user")
        )
        database_name, username = result.fetchone()

        print(f"Connected database: {database_name}")
        print(f"Connected user: {username}")


if __name__ == "__main__":
    test_database_connection()