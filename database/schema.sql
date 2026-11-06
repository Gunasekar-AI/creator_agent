-- =========================================
-- DEV TABLES (5)
-- =========================================

CREATE TABLE IF NOT EXISTS dev_planner_mapping (
    mapping_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jira_ticket_id VARCHAR(50) NOT NULL,
    component_name VARCHAR(100),
    test_case_id BIGINT NOT NULL,
    test_layer VARCHAR(30),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dev_generated_scripts (
    script_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    test_case_id BIGINT NOT NULL,
    script_name VARCHAR(200) NOT NULL,
    script_path TEXT NOT NULL,
    script_version INTEGER NOT NULL DEFAULT 1 CHECK (script_version > 0),
    git_branch VARCHAR(200),
    pr_id VARCHAR(100),
    pr_status VARCHAR(30),
    review_feedback TEXT,
    script_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dev_execution (
    execution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    script_id BIGINT NOT NULL REFERENCES dev_generated_scripts(script_id),
    execution_type VARCHAR(30),
    framework_name VARCHAR(100),
    execution_status VARCHAR(30) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    rollback_status VARCHAR(30),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS dev_execution_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES dev_execution(execution_id),
    total_tests INTEGER NOT NULL DEFAULT 0 CHECK (total_tests >= 0),
    passed_tests INTEGER NOT NULL DEFAULT 0 CHECK (passed_tests >= 0),
    failed_tests INTEGER NOT NULL DEFAULT 0 CHECK (failed_tests >= 0),
    skipped_tests INTEGER NOT NULL DEFAULT 0 CHECK (skipped_tests >= 0),
    execution_time_ms BIGINT CHECK (execution_time_ms >= 0),
    result_status VARCHAR(20) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (passed_tests + failed_tests + skipped_tests <= total_tests)
);

CREATE TABLE IF NOT EXISTS dev_promotion_eligibility (
    eligibility_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES dev_execution(execution_id),
    pass_percentage NUMERIC(5,2) NOT NULL CHECK (pass_percentage BETWEEN 0 AND 100),
    failure_count INTEGER NOT NULL DEFAULT 0 CHECK (failure_count >= 0),
    threshold_value NUMERIC(5,2) NOT NULL CHECK (threshold_value BETWEEN 0 AND 100),
    eligibility_status VARCHAR(30) NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================================
-- QA TABLES (4)
-- =========================================

CREATE TABLE IF NOT EXISTS qa_test_plan (
    plan_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    jira_test_plan_id VARCHAR(100),
    source_build_version VARCHAR(100),
    plan_name VARCHAR(200) NOT NULL,
    contract_count INTEGER NOT NULL DEFAULT 0 CHECK (contract_count >= 0),
    component_count INTEGER NOT NULL DEFAULT 0 CHECK (component_count >= 0),
    integration_count INTEGER NOT NULL DEFAULT 0 CHECK (integration_count >= 0),
    regression_count INTEGER NOT NULL DEFAULT 0 CHECK (regression_count >= 0),
    e2e_count INTEGER NOT NULL DEFAULT 0 CHECK (e2e_count >= 0),
    plan_status VARCHAR(30) NOT NULL,
    approval_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qa_test_plan_cases (
    plan_case_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES qa_test_plan(plan_id) ON DELETE CASCADE,
    test_case_id BIGINT NOT NULL,
    script_id BIGINT,
    test_layer VARCHAR(30) NOT NULL,
    selection_type VARCHAR(30),
    selection_reason TEXT,
    execution_order INTEGER CHECK (execution_order IS NULL OR execution_order > 0)
);

CREATE TABLE IF NOT EXISTS qa_execution (
    execution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES qa_test_plan(plan_id),
    script_id BIGINT NOT NULL,
    script_version INTEGER NOT NULL CHECK (script_version > 0),
    execution_type VARCHAR(30),
    framework_name VARCHAR(100),
    execution_status VARCHAR(30) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    rollback_status VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS qa_execution_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    execution_id BIGINT NOT NULL REFERENCES qa_execution(execution_id),
    total_tests INTEGER NOT NULL DEFAULT 0 CHECK (total_tests >= 0),
    passed_tests INTEGER NOT NULL DEFAULT 0 CHECK (passed_tests >= 0),
    failed_tests INTEGER NOT NULL DEFAULT 0 CHECK (failed_tests >= 0),
    skipped_tests INTEGER NOT NULL DEFAULT 0 CHECK (skipped_tests >= 0),
    result_status VARCHAR(20) NOT NULL,
    defect_id VARCHAR(100),
    defect_status VARCHAR(30),
    jira_sync_status VARCHAR(30),
    report_location TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (passed_tests + failed_tests + skipped_tests <= total_tests)
);

-- =========================================
-- STAGING TABLES (4)
-- =========================================

CREATE TABLE IF NOT EXISTS staging_deployment (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    build_version VARCHAR(100) NOT NULL,
    git_commit_id VARCHAR(100),
    deployment_status VARCHAR(30) NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deployed_by VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS staging_test_plan (
    staging_plan_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deployment_id BIGINT NOT NULL REFERENCES staging_deployment(deployment_id),
    plan_name VARCHAR(200) NOT NULL,
    selection_criteria VARCHAR(30) NOT NULL,
    jira_story_id VARCHAR(100),
    jira_epic_id VARCHAR(100),
    total_test_cases INTEGER NOT NULL DEFAULT 0 CHECK (total_test_cases >= 0),
    plan_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS staging_execution (
    execution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staging_plan_id BIGINT NOT NULL REFERENCES staging_test_plan(staging_plan_id),
    deployment_id BIGINT NOT NULL REFERENCES staging_deployment(deployment_id),
    script_id BIGINT NOT NULL,
    script_version INTEGER NOT NULL CHECK (script_version > 0),
    framework_name VARCHAR(100),
    execution_status VARCHAR(30) NOT NULL,
    rollback_status VARCHAR(30),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS staging_release_report (
    report_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deployment_id BIGINT NOT NULL REFERENCES staging_deployment(deployment_id),
    execution_id BIGINT NOT NULL REFERENCES staging_execution(execution_id),
    total_tests INTEGER NOT NULL DEFAULT 0 CHECK (total_tests >= 0),
    passed_tests INTEGER NOT NULL DEFAULT 0 CHECK (passed_tests >= 0),
    failed_tests INTEGER NOT NULL DEFAULT 0 CHECK (failed_tests >= 0),
    coverage_percentage NUMERIC(5,2) CHECK (coverage_percentage BETWEEN 0 AND 100),
    human_acceptance VARCHAR(30),
    sprint_signoff VARCHAR(30),
    release_signoff VARCHAR(30),
    report_location TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (passed_tests + failed_tests <= total_tests)
);

-- =========================================
-- INDEXES
-- =========================================

CREATE INDEX IF NOT EXISTS idx_dev_mapping_ticket
    ON dev_planner_mapping(jira_ticket_id);

CREATE INDEX IF NOT EXISTS idx_dev_scripts_test_case
    ON dev_generated_scripts(test_case_id);

CREATE INDEX IF NOT EXISTS idx_dev_execution_script
    ON dev_execution(script_id);

CREATE INDEX IF NOT EXISTS idx_qa_plan_cases_plan
    ON qa_test_plan_cases(plan_id);

CREATE INDEX IF NOT EXISTS idx_qa_execution_plan
    ON qa_execution(plan_id);

CREATE INDEX IF NOT EXISTS idx_staging_plan_deployment
    ON staging_test_plan(deployment_id);

CREATE INDEX IF NOT EXISTS idx_staging_execution_plan
    ON staging_execution(staging_plan_id);