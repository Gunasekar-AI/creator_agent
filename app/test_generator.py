import ast
import json
import os
import re
from pathlib import Path

from app.change_detector import PROJECT_ROOT
from dotenv import load_dotenv
from groq import BadRequestError, Groq


load_dotenv(PROJECT_ROOT / ".env", override=False)

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def get_groq_client():
    """Create a Groq client after checking the API key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing from .env")
    return Groq(api_key=api_key)


def jira_description_to_text(value):
    """Convert Jira plain text or Atlassian rich text to text."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts = [jira_description_to_text(item) for item in value]
        return "\n".join(part for part in parts if part)

    if isinstance(value, dict):
        if value.get("type") == "text":
            return value.get("text", "")

        if value.get("content") is not None:
            return jira_description_to_text(value["content"])

        return value.get("text", "")

    return str(value)


def call_groq(system_prompt, user_prompt):
    """Call Groq and return its JSON response text."""
    client = get_groq_client()

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=8192,
            response_format={"type": "json_object"},
        )
    except BadRequestError as exc:
        print("Groq rejected the generation request.")
        print("Check the model, prompt size, and JSON response requirements.")
        print("Groq error details:", str(exc))
        raise

    choice = response.choices[0]
    content = choice.message.content or ""

    print("\n--- GROQ RESPONSE DEBUG ---")
    print("Model:", MODEL)
    print("Finish reason:", choice.finish_reason)
    print("Response content:")
    print(repr(content))
    print("--- END GROQ RESPONSE DEBUG ---\n")

    if choice.finish_reason == "length":
        raise RuntimeError(
            "Groq reached its output-token limit. Reduce the prompt/output "
            "size or choose a model with a sufficient output-token limit."
        )

    if not content.strip():
        raise RuntimeError("Groq returned an empty response.")

    return content


def parse_json_response(response_text):
    """Parse a JSON object returned by Groq."""
    cleaned = (response_text or "").strip()

    cleaned = re.sub(
        r"\A\s*```(?:json)?[ \t]*\r?\n?",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\r?\n?```[ \t]*\Z", "", cleaned)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Groq returned invalid JSON: {exc}. "
            f"Response begins with: {cleaned[:500]!r}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError("Groq response must be a JSON object.")

    return result


def normalize_generated_code(code):
    """Remove Markdown fences and normalize escaped AI-generated source."""
    if not isinstance(code, str):
        raise ValueError("Generated code must be a string.")

    code = code.strip()

    if not code:
        return ""

    code = re.sub(
        r"\A```(?:python|gherkin|karate|feature)?[ \t]*\r?\n?",
        "",
        code,
        count=1,
        flags=re.IGNORECASE,
    )
    code = re.sub(r"\r?\n?```[ \t]*\Z", "", code)

    # Normalize double-escaped line breaks and tabs.
    code = code.replace("\\\\r\\\\n", "\n")
    code = code.replace("\\\\n", "\n")
    code = code.replace("\\\\t", "\t")

    # Normalize single-escaped line breaks and tabs.
    code = code.replace("\\r\\n", "\n")
    code = code.replace("\\n", "\n")
    code = code.replace("\\t", "\t")

    return code.strip()


def assign_missing_test_ids(test_cases):
    """Assign sequential IDs when the extractor omits them."""
    for index, case in enumerate(test_cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(
                f"Test case at position {index} must be a JSON object."
            )

        if not case.get("test_id"):
            case["test_id"] = f"TC-{index:03d}"

        case["test_type"] = str(
            case.get("test_type", "other")
        ).strip().lower()

    return test_cases


def extract_test_cases(ticket):
    """Extract structured test cases from Jira using Groq."""
    description = jira_description_to_text(ticket.get("description"))

    ticket_text = f"""
Jira Issue: {ticket.get('issue_key', '')}
Summary: {ticket.get('summary', '')}
Issue Type: {ticket.get('issue_type', '')}
Labels: {ticket.get('labels', [])}

Description and Test Plan:
{description}
"""

    system_prompt = """
You are a QA test analyst.

Extract test cases strictly from the supplied Jira issue.

Rules:
- Preserve Jira test IDs when available.
- If a test ID is missing, assign TC-001, TC-002, etc.
- Classify each case as ui, api, or other.
- Do not invent additional scenarios.
- Do not invent URLs, selectors, credentials, endpoints,
  business rules, or expected results.
- Put unspecified information in missing_details.
- Return an empty test_cases array only when no test cases exist.

Return exactly one valid JSON object:
{
  "test_cases": [
    {
      "test_id": "TC-001",
      "test_type": "ui",
      "title": "Valid login",
      "preconditions": [],
      "steps": [],
      "expected_result": "",
      "missing_details": []
    }
  ]
}
"""

    result = parse_json_response(
        call_groq(system_prompt, ticket_text)
    )

    if not isinstance(result.get("test_cases"), list):
        raise ValueError("Groq did not return a test_cases list.")

    result["test_cases"] = assign_missing_test_ids(
        result["test_cases"]
    )

    return result


def _normalized_test_id(test_id):
    """Convert a Jira test ID into a safe Python function-name component."""
    return re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        str(test_id),
    ).strip("_").lower()


def _validate_ui_script(ui_script, ui_test_cases):
    """Validate Python syntax and test functions."""
    if not ui_test_cases:
        if ui_script:
            raise ValueError(
                "Groq generated UI tests, but Jira contains no UI cases."
            )
        return

    if not ui_script:
        raise ValueError(
            "Jira contains UI test cases, but Groq generated an empty UI script."
        )

    try:
        tree = ast.parse(ui_script)
    except SyntaxError as exc:
        raise ValueError(
            f"Generated UI script has invalid Python syntax: {exc}; "
            f"line={exc.lineno}, source={exc.text!r}"
        ) from exc

    function_nodes = {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    test_functions = {
        name: node
        for name, node in function_nodes.items()
        if name.startswith("test_")
    }

    for case in ui_test_cases:
        test_id = case.get("test_id")

        if not test_id:
            raise ValueError("A UI test case is missing its test_id.")

        normalized_id = _normalized_test_id(test_id)

        if not normalized_id:
            raise ValueError(f"Invalid UI test ID: {test_id!r}")

        pattern = re.compile(
            rf"^test_{re.escape(normalized_id)}(?:_\w+)?$"
        )

        matches = [
            name for name in test_functions
            if pattern.fullmatch(name)
        ]

        if not matches:
            raise ValueError(
                f"Generated UI script is missing a pytest function "
                f"for {test_id}. Found: {sorted(test_functions)}"
            )

    # Validate logout only when Jira explicitly requests it.
    logout_cases = [
        case for case in ui_test_cases
        if "logout" in str(case.get("title", "")).lower()
        or "logout" in str(case.get("expected_result", "")).lower()
    ]

    for case in logout_cases:
        normalized_id = _normalized_test_id(case["test_id"])

        matching_name = next(
            (
                name for name in test_functions
                if re.fullmatch(
                    rf"test_{re.escape(normalized_id)}(?:_\w+)?",
                    name,
                )
            ),
            None,
        )

        if not matching_name:
            continue

        node = test_functions[matching_name]
        lines = ui_script.splitlines()
        end_line = getattr(node, "end_lineno", node.lineno)

        function_body = "\n".join(
            lines[node.lineno - 1:end_line]
        )

        if "logout-button" not in function_body:
            raise ValueError(
                f"{matching_name} does not use logout-button."
            )

        if not re.search(r"\.click\s*\(", function_body):
            raise ValueError(
                f"{matching_name} does not click the logout button."
            )

        if re.search(
            r"pytest\.(?:fail|skip|mark\.xfail)\s*\(",
            function_body,
        ):
            raise ValueError(
                f"{matching_name} contains a placeholder failure, skip, or xfail."
            )


def _validate_api_script(api_script, api_test_cases):
    """Validate Karate output only when API cases exist."""
    if api_test_cases and not api_script:
        raise ValueError(
            "Jira contains API test cases, but Groq generated an empty Karate script."
        )

    if api_script and not api_test_cases:
        raise ValueError(
            "Groq generated API tests, but Jira contains no API test cases."
        )

    if api_script and not re.search(
        r"^\s*Feature\s*:",
        api_script,
        flags=re.MULTILINE,
    ):
        raise ValueError(
            "Generated Karate script is missing its Feature declaration."
        )


def _normalize_missing_details(value):
    """Accept either a JSON array or a JSON-encoded array."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [value] if value.strip() else []

    if not isinstance(value, list):
        raise ValueError(
            "Groq missing_details must be a JSON array "
            "or a JSON-encoded array."
        )

    return value


def generate_automation_scripts(ticket, test_cases):
    """Generate and validate Selenium pytest and Karate source code."""
    description = jira_description_to_text(ticket.get("description"))

    ui_test_cases = [
        case for case in test_cases
        if case.get("test_type") == "ui"
    ]

    api_test_cases = [
        case for case in test_cases
        if case.get("test_type") == "api"
    ]

    base_url = os.getenv("BASE_URL", "").strip().rstrip("/")

    if not base_url:
        raise ValueError("BASE_URL is missing from .env")

    prompt = f"""
JIRA ISSUE
----------
Issue: {ticket.get('issue_key', '')}
Summary: {ticket.get('summary', '')}
Issue type: {ticket.get('issue_type', '')}

JIRA DESCRIPTION
----------------
{description}

EXTRACTED TEST CASES
--------------------
{json.dumps(test_cases, indent=2, ensure_ascii=False)}

APPLICATION CONFIGURATION
-------------------------
BASE_URL: {base_url}

Known UI selectors:
- Username field ID: username
- Password field ID: password
- Login button ID: login-button
- Logout button ID: logout-button
- Login status ID: login-status
- Dashboard section ID: dashboard-section
- Dashboard title ID: dashboard-title
- Dashboard message ID: dashboard-message

Credentials:
- Username environment variable: TEST_USERNAME
- Password environment variable: TEST_PASSWORD

Never hardcode, print, or include actual credentials in generated code.

Known application behavior:
- Invalid login message: Invalid username or password
- Successful login message: Login successful
- Dashboard title: Dashboard
- Dashboard message: Welcome to the QA Demo Application

BASE_URL is the login page URL.
The selectors above are supplied configuration and must not be
reported as missing details.

API configuration:
- API base URL: BASE_URL
- Login endpoint path: /api/login
- HTTP method: POST
- Credentials must come from environment variables.

TEST GENERATION RULES
---------------------
1. Generate only scenarios explicitly present in extracted test cases.
2. Do not invent additional scenarios.
3. Do not add invalid-login, logout, or API tests unless Jira requests them.
4. Generate one pytest function per UI test case.
5. Include the Jira test ID in every pytest function name.
6. Generate Karate scenarios only for API cases.
7. If no UI cases exist, ui_pytest must be an empty string.
8. If no API cases exist, api_karate must be an empty string.
9. Do not generate tests for cases classified as other.

SELENIUM RULES
--------------
1. Use pytest and Selenium.
2. Include all imports and a working browser fixture when UI cases exist.
3. Use yield and close the browser in finally.
4. Use explicit waits and meaningful assertions.
5. Read BASE_URL, TEST_USERNAME, TEST_PASSWORD using os.getenv.
6. Never print or hardcode credentials.
7. Do not force headless mode.
8. Set window size to 1920x1080.
9. If CHROME_BIN is set, configure options.binary_location.
10. If CHROMEDRIVER_PATH is set, import Service from
    selenium.webdriver.chrome.service and use:
    webdriver.Chrome(service=Service(driver_path), options=options).
11. Otherwise use Selenium driver discovery.
12. Never use executable_path, input(), TODOs, placeholder failures, or skips.
13. Use the supplied selectors.
14. Name tests using the Jira ID, e.g. test_tc_001_successful_login.

KARATE RULES
------------
1. Generate valid Karate feature syntax.
2. Read credentials from environment variables.
3. Verify expected HTTP status and response fields from Jira.
4. Do not invent API scenarios, endpoints, or response fields.
5. Return an empty string if there are no API cases.

MISSING DETAILS
---------------
Report only genuinely required information not supplied here.
Do not report the supplied URL, selectors, or application messages as missing.

OUTPUT
------
Return exactly one valid JSON object with these keys:
ui_pytest, api_karate, missing_details.

Source code values must be valid JSON strings.
Return no Markdown fences or explanation outside the JSON object.
"""

    system_prompt = """
You are a senior test automation engineer.

Generate executable automation code strictly from the supplied Jira
test cases and application configuration.

Do not invent scenarios or test layers.

Python:
- Use pytest and Selenium.
- Include imports and a working browser fixture when UI cases exist.
- Use explicit waits and meaningful assertions.
- Close the browser in finally.
- Support CHROME_BIN and CHROMEDRIVER_PATH using Selenium Service.
- Do not force headless mode.
- Do not use input(), TODOs, placeholder failures, or skips.
- Read credentials from environment variables.
- Generate one pytest function per UI case.
- Include each Jira test ID in its function name.

Karate:
- Generate valid Karate syntax only for supplied API cases.
- Verify expected HTTP status and response fields.
- Return an empty string if there are no API cases.

Return exactly one valid JSON object with keys:
ui_pytest, api_karate, missing_details.

Source values must be valid JSON strings.
Return no Markdown fences or explanation.
"""

    result = parse_json_response(
        call_groq(system_prompt, prompt)
    )

    for key in ("ui_pytest", "api_karate", "missing_details"):
        if key not in result:
            raise ValueError(
                f"Groq response is missing required key: {key}"
            )

    result["missing_details"] = _normalize_missing_details(
        result["missing_details"]
    )

    ui_script = normalize_generated_code(result["ui_pytest"])
    api_script = normalize_generated_code(result["api_karate"])

    result["ui_pytest"] = ui_script
    result["api_karate"] = api_script

    _validate_ui_script(ui_script, ui_test_cases)
    _validate_api_script(api_script, api_test_cases)

    # IMPORTANT: Return the generated dictionary to generate_scripts().
    return result


def _write_text(path, content):
    """Write UTF-8 text, creating parent folders if necessary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_scripts(ticket):
    """Generate test artifacts from Jira without publishing them."""
    print("AI Test Generator Started")
    print("Issue:", ticket.get("issue_key"))
    print("Summary:", ticket.get("summary"))

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing from .env")

    issue_key = ticket.get("issue_key")

    if not issue_key:
        raise ValueError("Jira ticket is missing issue_key.")

    extracted = extract_test_cases(ticket)
    test_cases = extracted["test_cases"]

    if not test_cases:
        raise ValueError(
            f"No valid test cases were extracted for {issue_key}."
        )

    test_cases = assign_missing_test_ids(test_cases)
    extracted["test_cases"] = test_cases

    print(json.dumps(test_cases, indent=2, ensure_ascii=False))
    print("Test cases extracted:", len(test_cases))

    output_dir = PROJECT_ROOT / "generated_tests" / issue_key
    output_dir.mkdir(parents=True, exist_ok=True)

    ui_path = output_dir / "test_ui.py"
    api_path = output_dir / "test_api.feature"

    # Generate and validate before removing existing valid artifacts.
    generated = generate_automation_scripts(ticket, test_cases)

    if not isinstance(generated, dict):
        raise TypeError(
            "generate_automation_scripts() must return a dictionary."
        )

    ui_script = generated["ui_pytest"]
    api_script = generated["api_karate"]
    missing = generated["missing_details"]

    # Remove stale scripts only after successful generation and validation.
    for stale_path in (ui_path, api_path):
        if stale_path.exists():
            stale_path.unlink()
    # Synchronize missing details with the generation response.
    for case in extracted["test_cases"]:
        case["missing_details"] = []
        
    # Save test cases with normalized IDs.
    _write_text(
        output_dir / "test_cases.json",
        json.dumps(extracted, indent=2, ensure_ascii=False),
    )

    # Write only the requested test layers.
    if ui_script:
        _write_text(ui_path, ui_script + "\n")

    if api_script:
        _write_text(api_path, api_script + "\n")

    _write_text(
        output_dir / "missing_details.txt",
        "\n".join(str(item) for item in missing)
        + ("\n" if missing else ""),
    )

    print("Generated test files in:", output_dir.resolve())

    if missing:
        print("Some details need to be configured:")
        for detail in missing:
            print("-", detail)

    print("UI test generated:", bool(ui_script))
    print("API test generated:", bool(api_script))

    return generated


if __name__ == "__main__":
    from app.jira_reader import JiraReader

    print("Starting manual Jira test generation...")

    jira = JiraReader()
    ticket = jira.get_ticket("SCRUM-16")

    result = generate_scripts(ticket)

    print("Generation finished.")
    print(json.dumps(result, indent=2, ensure_ascii=False))
