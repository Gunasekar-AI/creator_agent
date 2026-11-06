from sqlalchemy import text
from app.db.database import engine


def test_database_crud():
    with engine.begin() as connection:
        # Insert a temporary test mapping
        result = connection.execute(
            text("""
                INSERT INTO dev_planner_mapping
                    (jira_ticket_id, component_name, test_case_id,
                     test_layer, status)
                VALUES
                    (:ticket, :component, :test_case, :layer, :status)
                RETURNING mapping_id
            """),
            {
                "ticket": "DB-TEST-001",
                "component": "Login",
                "test_case": 1001,
                "layer": "UI",
                "status": "SELECTED",
            },
        )

        mapping_id = result.scalar_one()

        # Read the inserted record
        row = connection.execute(
            text("""
                SELECT jira_ticket_id, component_name, test_case_id, status
                FROM dev_planner_mapping
                WHERE mapping_id = :mapping_id
            """),
            {"mapping_id": mapping_id},
        ).fetchone()

        print("Inserted mapping:", row)

        # Delete the temporary test record
        connection.execute(
            text("""
                DELETE FROM dev_planner_mapping
                WHERE mapping_id = :mapping_id
            """),
            {"mapping_id": mapping_id},
        )

        print("Database INSERT, SELECT and DELETE successful")


if __name__ == "__main__":
    test_database_crud()