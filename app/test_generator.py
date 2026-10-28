
import ast
import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from groq import BadRequestError, Groq

from app.git_publisher import publish_generated_tests


load_dotenv()

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
    print("\\n--- GROQ RESPONSE DEBUG ---")
    print("Model:", MODEL)
    print("Finish reason:", choice.finish_reason)
    print("Response content:")
    print(repr(content))
    print("--- END GROQ RESPONSE DEBUG ---\\n")

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
    """Remove optional Markdown fences from generated source."""
    if not isinstance(code, str):
        return ""

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

    return code.strip()


def normalize_generated_code(code):
    """Remove optional Markdown fences from generated source."""
    if not isinstance(code, str):
        return ""
    code = code.strip()
    if not code:
        return ""
    code = re.sub(
        r"\\A```(?:python|gherkin|karate|feature)?[ \\t]*\\r?\\n?",
        "",
        code,
        count=1,
        flags=re.IGNORECASE,
    )
    code = re.sub(r"\\r?\\n?```[ \\t]*\\Z", "", code)
    return code.strip()


def extract_test_cases(ticket):
    """Extract structured test cases from a Jira issue using Groq."""
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
You are a QA test analyst. Extract test cases strictly from the supplied
Jira issue. Do not invent URLs, API endpoints, selectors, credentials,
business rules, or expected results. Preserve test IDs when available.
Classify each case as ui, api, or other. If a detail is unspecified, use
null or an empty value and list it in missing_details.

Return one valid JSON object only, with this structure:
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
    result = parse_json_response(call_groq(system_prompt, ticket_text))
    if not isinstance(result.get("test_cases"), list):
        raise ValueError("Groq did not return a test_cases list.")
    return result


def generate_automation_scripts(ticket, test_cases):
    """Generate and validate Selenium pytest and Karate source code."""
    description = jira_description_to_text(ticket.get("description"))
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
UI base URL: http://127.0.0.1:8001/
Username field ID: username
Password field ID: password
Login button ID: login-button
Logout button ID: logout-button
Login status element ID: login-status
Dashboard section ID: dashboard-section
Dashboard title element ID: dashboard-title
Dashboard message element ID: dashboard-message

Valid username: testuser
Valid password: Password123
Invalid username: invalid_user
Invalid password: WrongPassword123

Invalid login message: Invalid username or password
Successful login message: Login successful
Dashboard title: Dashboard
Dashboard message: Welcome to the QA Demo Application

API endpoint: http://127.0.0.1:8001/api/login
API method: POST
Valid API payload:
{{"username": "testuser", "password": "Password123"}}

Expected successful API response:
success=true
message="Login successful"
username="testuser"

MANDATORY PYTHON TEST FUNCTION NAMES
------------------------------------
Use these exact names:
- test_tc_001_login_with_valid_credentials
- test_tc_002_login_with_invalid_credentials
- test_tc_003_logout_successfully

GENERATION RULES
----------------
1. Use Jira and extracted test cases as the source of truth for coverage.
2. Generate Selenium pytest tests for UI cases and a Karate feature for API
   cases. Include all imports and the browser fixture in ui_pytest.
3. Never generate pseudocode, TODOs, empty tests, or placeholder failures.
4. Use only the configuration above for selectors, URLs, credentials,
   messages, and application behavior.
5. Use Selenium explicit waits and meaningful assertions.
6. TC-001: open the UI, enter valid credentials, click login-button, wait
   for dashboard-title to be visible, assert title Dashboard and message
   Welcome to the QA Demo Application. Do not wait for login-status to
   remain visible after successful login.
7. TC-002: open the UI, enter invalid credentials, click login-button, wait
   for login-status to be visible, assert its error text, and assert
   dashboard-section is hidden.
8. TC-003: log in first, wait for dashboard-title, locate logout using
   By.ID, "logout-button", click it, wait for username to be visible, and
   verify dashboard-section is hidden. Never guess another selector.
9. Use a pytest fixture with yield and close the browser in finally.
   Do not force headless mode. Set window size to 1920x1080. If CHROME_BIN
   is set, configure options.binary_location. If CHROMEDRIVER_PATH is set,
   use it for ChromeDriver; otherwise use Selenium driver discovery.
   Never use input() or pause for keyboard input.
10. Generate API tests only for API cases in Jira. If TC-004 is present,
    generate a Karate test using the configured endpoint, method, payload,
    and expected response fields.
11. Report genuinely missing information in missing_details.
12. Return exactly one valid JSON object with keys ui_pytest, api_karate,
    and missing_details. Source code values must be valid JSON strings.
    Return no Markdown fences or explanation outside the JSON.
"""
    system_prompt = """
You are a senior test automation engineer. Return exactly one valid JSON
object with keys ui_pytest, api_karate, and missing_details.

Python:
- Use pytest and Selenium; include all imports and a working browser fixture.
- Use explicit waits and meaningful assertions.
- Close the browser in try/finally.
- Support CHROME_BIN and CHROMEDRIVER_PATH if configured.
- Do not force headless mode, use input(), TODOs, empty tests, placeholders,
  or skips.
- Use dashboard visibility to confirm successful login.
- Use By.ID, "logout-button" for logout and verify logged-out state.
- Use the exact function names specified in the prompt.

Karate:
- Generate valid Karate syntax for the supplied API cases.
- Verify expected HTTP status and response fields.
- If no API case is present, api_karate may be an empty string.

Missing information:
- Report only genuinely required details not supplied.
- Do not list values already supplied or invent behavior.

JSON:
- Source values must be valid JSON strings.
- Return no Markdown fences or explanation outside the JSON object.
"""
    result = parse_json_response(call_groq(system_prompt, prompt))

    for key in ("ui_pytest", "api_karate", "missing_details"):
        if key not in result:
            raise ValueError(f"Groq response is missing required key: {key}")
    if not isinstance(result["missing_details"], list):
        raise ValueError("missing_details must be a JSON array.")

    ui_script = normalize_generated_code(result.get("ui_pytest"))
    api_script = normalize_generated_code(result.get("api_karate"))
    result["ui_pytest"] = ui_script
    result["api_karate"] = api_script

    if not ui_script:
        raise ValueError("Groq generated an empty UI pytest script.")
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

    required_patterns = {
        "TC-001": re.compile(r"^test_tc_001_\w+$"),
        "TC-002": re.compile(r"^test_tc_002_\w+$"),
        "TC-003": re.compile(r"^test_tc_003_\w+$"),
    }

    for test_id, pattern in required_patterns.items():
        matches = [
            name for name in function_nodes
            if pattern.match(name)
        ]

        if not matches:
            test_names = sorted(
                name for name in function_nodes
                if name.startswith("test_")
            )
            raise ValueError(
                f"Generated UI script is missing a test function for "
                f"{test_id}. Found test functions: {test_names}"
            )

    logout_name = next(
        name for name in function_nodes
        if required_patterns["TC-003"].match(name)
    )

    logout_node = function_nodes[logout_name]
    lines = ui_script.splitlines()
    end_line = getattr(
        logout_node, "end_lineno", logout_node.lineno
    )
    logout_body = "\n".join(
        lines[logout_node.lineno - 1:end_line]
    )

    if "logout-button" not in logout_body:
        raise ValueError(
            f"{logout_name} does not use the configured logout-button ID."
        )

    if not re.search(r"\.click\s*\(", logout_body):
        raise ValueError(
            f"{logout_name} does not click the logout button."
        )

    if re.search(
        r"pytest\.(?:fail|skip|mark\.xfail)\s*\(",
        logout_body,
    ):
        raise ValueError(
            f"{logout_name} contains a placeholder failure, skip, or xfail."
        )

    if api_script and not re.search(
        r"^\s*Feature\s*:",
        api_script,
        flags=re.MULTILINE,
    ):
        raise ValueError(
            "Generated Karate script is missing its Feature declaration."
        )

    return result



def _write_text(path, content):
    """Write UTF-8 text, creating parent folders if necessary."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_scripts(ticket):
    """Generate test artifacts from Jira, save them, and publish to GitHub."""
    print("AI Test Generator Started")
    print("Issue:", ticket.get("issue_key"))
    print("Summary:", ticket.get("summary"))
    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing from .env")

    issue_key = ticket.get("issue_key") or "UNKNOWN"

    extracted = extract_test_cases(ticket)
    test_cases = extracted["test_cases"]
    print("Test cases extracted:", len(test_cases))

    generated = generate_automation_scripts(ticket, test_cases)
    ui_script = generated["ui_pytest"]
    api_script = generated["api_karate"]

    output_dir = Path("generated_tests") / issue_key
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_text(
        output_dir / "test_cases.json",
        json.dumps(extracted, indent=2, ensure_ascii=False),
    )
    
    if ui_script:
        _write_text(output_dir / "test_ui.py", ui_script + "\n")

    if api_script:
        _write_text(output_dir / "test_api.feature", api_script + "\n")

    missing = generated["missing_details"]

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

    publish_result = publish_generated_tests(
        issue_key=issue_key,
        labels=ticket.get("labels", []),
        output_dir=output_dir,
        repo_dir=Path.cwd(),
        base_branch=os.getenv("GIT_BASE_BRANCH", "main"),
        summary=ticket.get("summary", ""),
    )
    print("Git publishing completed:", publish_result)
    if isinstance(publish_result, dict):
        print("Pull request URL:", publish_result.get("pr_url"))

    return {**generated, "git": publish_result}


if __name__ == "__main__":
    from app.jira_reader import JiraReader

    print("Starting manual Jira test generation...")
    jira = JiraReader()
    ticket = jira.get_ticket("SCRUM-2")
    result = generate_scripts(ticket)
    print("Generation finished.")
    print(json.dumps(result, indent=2, ensure_ascii=False))