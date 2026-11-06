# app/dev_execution_repository.py
from datetime import datetime, timezone

from sqlalchemy import text

from app.db.database import SessionLocal


def _now():
    return datetime.now(timezone.utc)


def persist_dev_execution(
    script_id: int,
    execution_status: str,
    framework_name: str = "pytest",
    execution_type: str = "MANUAL",
    started_at=None,
    completed_at=None,
    rollback_status: str = "not_required",
    error_message: str = None,
) -> int:
    """Insert dev_execution and return execution_id."""
    with SessionLocal() as db:
        try:
            row = db.execute(
                text("""
                    INSERT INTO dev_execution
                        (script_id, execution_type, framework_name,
                         execution_status, started_at, completed_at,
                         rollback_status, error_message)
                    VALUES
                        (:script_id, :execution_type, :framework_name,
                         :execution_status, :started_at, :completed_at,
                         :rollback_status, :error_message)
                    RETURNING execution_id
                """),
                {
                    "script_id": script_id,
                    "execution_type": execution_type,
                    "framework_name": framework_name,
                    "execution_status": execution_status,
                    "started_at": started_at or _now(),
                    "completed_at": completed_at,
                    "rollback_status": rollback_status,
                    "error_message": error_message,
                },
            ).scalar_one()
            db.commit()
            return row
        except Exception:
            db.rollback()
            raise


def persist_dev_execution_results(
    execution_id: int,
    total_tests: int,
    passed_tests: int,
    failed_tests: int,
    skipped_tests: int,
    result_status: str,
    execution_time_ms: int = None,
) -> int:
    """Insert dev_execution_results and return result_id."""
    if passed_tests + failed_tests + skipped_tests > total_tests:
        raise ValueError(
            "Test counts exceed total: "
            f"{passed_tests}+{failed_tests}+{skipped_tests} > {total_tests}"
        )
    if result_status not in {"PASS", "FAIL", "PARTIAL"}:
        raise ValueError(f"Invalid result_status: {result_status}")

    with SessionLocal() as db:
        try:
            row = db.execute(
                text("""
                    INSERT INTO dev_execution_results
                        (execution_id, total_tests, passed_tests,
                         failed_tests, skipped_tests, execution_time_ms,
                         result_status, executed_at)
                    VALUES
                        (:execution_id, :total_tests, :passed_tests,
                         :failed_tests, :skipped_tests, :execution_time_ms,
                         :result_status, :executed_at)
                    RETURNING result_id
                """),
                {
                    "execution_id": execution_id,
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "skipped_tests": skipped_tests,
                    "execution_time_ms": execution_time_ms,
                    "result_status": result_status,
                    "executed_at": _now(),
                },
            ).scalar_one()
            db.commit()
            return row
        except Exception:
            db.rollback()
            raise


def evaluate_promotion_eligibility(
    execution_id: int,
    total_tests: int,
    passed_tests: int,
    threshold_value: float = 95.0,
) -> dict:
    """Compute pass %, decide eligibility, insert dev_promotion_eligibility."""
    if total_tests <= 0:
        raise ValueError("total_tests must be > 0")

    pass_percentage = round(passed_tests / total_tests * 100, 2)
    failure_count = total_tests - passed_tests

    eligible = pass_percentage >= threshold_value and failure_count == 0
    eligibility_status = "ELIGIBLE" if eligible else "NOT_ELIGIBLE"

    with SessionLocal() as db:
        try:
            eligibility_id = db.execute(
                text("""
                    INSERT INTO dev_promotion_eligibility
                        (execution_id, pass_percentage, failure_count,
                         threshold_value, eligibility_status, evaluated_at)
                    VALUES
                        (:execution_id, :pass_percentage, :failure_count,
                         :threshold_value, :eligibility_status, :evaluated_at)
                    RETURNING eligibility_id
                """),
                {
                    "execution_id": execution_id,
                    "pass_percentage": pass_percentage,
                    "failure_count": failure_count,
                    "threshold_value": threshold_value,
                    "eligibility_status": eligibility_status,
                    "evaluated_at": _now(),
                },
            ).scalar_one()
            db.commit()
        except Exception:
            db.rollback()
            raise

    return {
        "eligibility_id": eligibility_id,
        "execution_id": execution_id,
        "pass_percentage": pass_percentage,
        "failure_count": failure_count,
        "threshold_value": threshold_value,
        "eligibility_status": eligibility_status,
    }