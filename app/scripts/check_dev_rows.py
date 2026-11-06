# scripts/check_dev_rows.py
"""
Verify that a DEV run wrote rows into all 5 DEV tables for one Jira issue.
Usage: python scripts/check_dev_rows.py SCRUM-2
"""
import sys
from sqlalchemy import text
from app.db.database import SessionLocal


def main(issue_key):
    with SessionLocal() as db:
        mapping = db.execute(
            text("""
                SELECT COUNT(*) FROM dev_planner_mapping
                WHERE jira_ticket_id = :k
            """),
            {"k": issue_key},
        ).scalar_one()

        scripts = db.execute(
            text("""
                SELECT COUNT(*)
                FROM dev_generated_scripts s
                JOIN dev_planner_mapping m
                  ON m.test_case_id = s.test_case_id
                WHERE m.jira_ticket_id = :k
            """),
            {"k": issue_key},
        ).scalar_one()

        executions = db.execute(
            text("""
                SELECT e.execution_id, e.execution_status,
                       r.result_status, r.total_tests,
                       r.passed_tests, r.failed_tests, r.skipped_tests
                FROM dev_execution e
                JOIN dev_execution_results r
                  ON r.execution_id = e.execution_id
                JOIN dev_generated_scripts s
                  ON s.script_id = e.script_id
                JOIN dev_planner_mapping m
                  ON m.test_case_id = s.test_case_id
                WHERE m.jira_ticket_id = :k
                ORDER BY e.execution_id DESC
                LIMIT 1
            """),
            {"k": issue_key},
        ).fetchone()

        gate = db.execute(
            text("""
                SELECT g.pass_percentage, g.failure_count,
                       g.threshold_value, g.eligibility_status
                FROM dev_promotion_eligibility g
                JOIN dev_execution e ON e.execution_id = g.execution_id
                JOIN dev_generated_scripts s ON s.script_id = e.script_id
                JOIN dev_planner_mapping m ON m.test_case_id = s.test_case_id
                WHERE m.jira_ticket_id = :k
                ORDER BY g.eligibility_id DESC
                LIMIT 1
            """),
            {"k": issue_key},
        ).fetchone()

    print(f"\nDEV rows for {issue_key}")
    print("-" * 50)
    print(f"dev_planner_mapping rows      : {mapping}")
    print(f"dev_generated_scripts rows    : {scripts}")
    if executions:
        (eid, estatus, rstatus, tot, ok, fail, skip) = executions
        print(f"dev_execution id              : {eid} ({estatus})")
        print(f"dev_execution_results status  : {rstatus}")
        print(f"  total={tot} passed={ok} failed={fail} skipped={skip}")
    else:
        print("dev_execution / results       : MISSING")
    if gate:
        (pct, fc, th, st) = gate
        print(f"dev_promotion_eligibility     : {st}")
        print(f"  pass={pct}% failures={fc} threshold={th}%")
    else:
        print("dev_promotion_eligibility     : MISSING")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_dev_rows.py ISSUE-KEY")
        raise SystemExit(1)
    main(sys.argv[1])