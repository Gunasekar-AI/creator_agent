from pathlib import Path
from sqlalchemy import text

from app.db.database import SessionLocal


def _get_value(data, *keys, default=None):
    """Return the first available value from a dictionary."""
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return default


def _get_test_layers(test_case):
    """Convert a test case's type into one or more execution layers."""
    test_type = str(
        _get_value(test_case, "test_type", "test_layer", "type", default="UI")
    ).strip().upper()

    if test_type in {"BOTH", "UI+API", "API+UI", "UI,API", "API,UI"}:
        return ["UI", "API"]

    if "API" in test_type:
        return ["API"]

    if "UI" in test_type:
        return ["UI"]

    return ["UI"]


def persist_generated_artifacts(
    issue_key: str,
    test_cases: list,
    output_dir: str | Path,
    git_branch: str,
):
    """
    Save generated test-case mappings and script records to DEV tables.

    One planner mapping is saved per test case and test layer.
    One generated-script record is saved per test case and test layer
    when the corresponding generated script file exists.
    """
    output_dir = Path(output_dir).resolve()

    ui_script = output_dir / "test_ui.py"
    api_script = output_dir / "test_api.feature"

    saved_mappings = 0
    saved_scripts = 0

    with SessionLocal() as db:
        try:
            for case in test_cases:
                test_case_id = _get_value(
                    case, "test_case_id", "test_id", "id", "case_id"
                )

                if test_case_id is None:
                    raise ValueError(
                        f"Test case is missing an ID: {case}"
                    )

                component_name = _get_value(
                    case,
                    "component_name",
                    "component",
                    default="General",
                )

                for layer in _get_test_layers(case):
                    db.execute(
                        text("""
                            INSERT INTO dev_planner_mapping
                                (
                                    jira_ticket_id,
                                    component_name,
                                    test_case_id,
                                    test_layer,
                                    status
                                )
                            VALUES
                                (
                                    :jira_ticket_id,
                                    :component_name,
                                    :test_case_id,
                                    :test_layer,
                                    :status
                                )
                        """),
                        {
                            "jira_ticket_id": issue_key,
                            "component_name": component_name,
                            "test_case_id": str(test_case_id),
                            "test_layer": layer,
                            "status": "SELECTED",
                        },
                    )
                    saved_mappings += 1

                    script_path = (
                        ui_script if layer == "UI" else api_script
                    )

                    if not script_path.is_file():
                        continue

                    result = db.execute(
                        text("""
                            INSERT INTO dev_generated_scripts
                                (
                                    test_case_id,
                                    script_name,
                                    script_path,
                                    script_version,
                                    git_branch,
                                    script_status
                                )
                            VALUES
                                (
                                    :test_case_id,
                                    :script_name,
                                    :script_path,
                                    :script_version,
                                    :git_branch,
                                    :script_status
                                )
                            RETURNING script_id
                        """),
                        {
                            "test_case_id": str(test_case_id),
                            "script_name": script_path.name,
                            "script_path": str(script_path),
                            "script_version": 1,
                            "git_branch": git_branch,
                            "script_status": "GENERATED",
                        },
                    )

                    result.scalar_one()
                    saved_scripts += 1

            db.commit()

        except Exception:
            db.rollback()
            raise

    return {
        "jira_ticket_id": issue_key,
        "mappings_saved": saved_mappings,
        "scripts_saved": saved_scripts,
    }