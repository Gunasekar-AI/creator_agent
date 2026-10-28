import ast
import json
import os
import re
from pathlib import Path

import pytest
from selenium import webdriver
from groq import Groq, BadRequestError
from dotenv import load_dotenv
from groq import Groq

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
    """Convert Jira description, including Atlassian rich text, to text."""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "\n".join(
            text
            for text in (jira_description_to_text(item) for item in value)
            if text
        )

    if isinstance(value, dict):
        if value.get("type") == "text":
            return value.get("text", "")

        content = value.get("content", [])
        if content:
            return jira_description_to_text(content)

        return value.get("text", "")

    return str(value)



def call_groq(system_prompt, user_prompt):
    """Call Groq and return the model's JSON text response."""
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
        print("Groq rejected the script-generation request.")
        print("Error details:", str(exc))
        raise

    choice = response.choices[0]
    content = choice.message.content or ""

    print("\n--- GROQ RESPONSE DEBUG ---")
    print("Finish reason:", choice.finish_reason)
    print("Response content:")
    print(repr(content))
    print("--- END RESPONSE DEBUG ---\n")

    if choice.finish_reason == "length":
        raise RuntimeError(
            "Groq reached its output-token limit. "
            "Reduce the requested script size or use a supported "
            "model with a larger output limit."
        )

    if not content.strip():
        raise RuntimeError("Groq returned an empty response.")

    return content





def parse_json_response(response_text):
    """Parse a Groq JSON response."""
    cleaned = response_text.strip()

    cleaned = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Groq returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError("Groq response must be a JSON object.")

    return result


def normalize_generated_code(code):
    """Remove optional Markdown fences from generated source."""
    if not isinstance(code, str):
        return ""

    code = code.strip()
    code = re.sub(
        r"^\s*```(?:python|gherkin|karate|feature)?[ \t]*\r?\n?",
        "",
        code,
        count=1,
        flags=re.IGNORECASE,
    )
    code = re.sub(r"\r?\n?```[ \t]*$", "", code)

    return code.strip()




def normalize_generated_code(code):
    """Normalize source code returned inside a JSON string."""
    if not isinstance(code, str):
        return ""

    code = code.strip()
    if not code:
        return ""

    # Remove optional Markdown code fences.
    code = re.sub(
        r"^\s*```(?:python|gherkin|karate|feature)?[ \t]*\r?\n?",
        "",
        code,
        count=1,
        flags=re.IGNORECASE,
    )
    code = re.sub(
        r"\r?\n?```[ \t]*$",
        "",
        code,
    )

    return code.strip()

def extract_test_cases(ticket):
    """Use Groq to extract structured test cases from a Jira ticket."""
    description = jira_description_to_text(ticket.get("description"))

    ticket_text = f"""
Jira Issue: {ticket.get('issue_key')}
Summary: {ticket.get('summary')}
Issue Type: {ticket.get('issue_type')}
Labels: {ticket.get('labels')}

Description and Test Plan:
{description}
"""

    system_prompt = """
You are a QA test analyst.

Extract test cases strictly from the supplied Jira ticket.

Rules:
- Do not invent URLs, API endpoints, selectors, credentials,
  business rules, or expected results.
- Preserve test IDs from the ticket when available.
- If a detail is unspecified, use null or an empty value and list
  missing information in missing_details.
- Classify each case as ui, api, or other.
- Return one valid JSON object only, using this structure:

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

    return result




def generate_automation_scripts(ticket, test_cases):
    """Generate and validate UI and API automation scripts using Groq."""
    description = jira_description_to_text(ticket.get("description"))

    prompt = f"""
JIRA ISSUE
----------
Issue: {ticket.get('issue_key')}
Summary: {ticket.get('summary')}
Issue type: {ticket.get('issue_type')}

JIRA DESCRIPTION
----------------
{description}

EXTRACTED TEST CASES
--------------------
{json.dumps(test_cases, indent=2, ensure_ascii=False)}

APPLICATION CONFIGURATION
-------------------------
Use these exact values for the QA demo application.

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

GENERATION RULES
----------------
1. Use the Jira description and extracted test cases as the source
   of truth for the requested test coverage.

2. Generate Selenium pytest tests for UI cases and Karate scenarios
   for API cases.

3. Preserve the test IDs and generate executable tests for all
   requested cases. Do not silently omit any case.

4. Never generate pseudocode, TODOs, empty test bodies, or placeholder
   failures for a requested test case.

5. Use the application configuration above. Do not invent selectors,
   URLs, endpoints, credentials, messages, or application behavior.

6. Use Selenium explicit waits and meaningful assertions.

7. TC-001: Valid login
   - Open the configured UI base URL.
   - Enter testuser and Password123.
   - Click the element with ID login-button.
   - Wait until the element with ID dashboard-title is visible.
   - Assert the title is Dashboard.
   - Assert the dashboard message is Welcome to the QA Demo Application.
   - Do not wait for login-status to remain visible after successful
     login because the login form may be hidden.

8. TC-002: Invalid login
   - Open the configured UI base URL.
   - Enter invalid_user and WrongPassword123.
   - Click the element with ID login-button.
   - Wait until login-status is visible.
   - Assert its text is Invalid username or password.
   - Assert dashboard-section is hidden.

9. TC-003: Logout successfully
   - Generate a real Selenium test named
     test_tc_003_logout_successfully.
   - Log in first using testuser and Password123.
   - Wait until dashboard-title is visible.
   - Locate the logout button using its exact ID:
     By.ID, "logout-button".
   - Use WebDriverWait and element_to_be_clickable if appropriate.
   - Click the logout button.
   - Wait until the username field with ID username is visible.
   - Verify that dashboard-section is hidden.
   - Do not use By.LINK_TEXT or guess another selector.
   - Never generate pytest.fail(), pytest.skip(), pytest.mark.xfail,
     or a missing-selector placeholder for this test.
   - The logout selector is provided and must not be reported missing.

10. Use a pytest fixture with yield and ensure the browser is closed
    in teardown, even if a test fails.

11. Support local Windows and GitHub Actions:
    - Do not force headless mode.
    - Set browser window size to 1920x1080.
    - If CHROME_BIN is set, configure Chrome's binary location.
    - If CHROMEDRIVER_PATH is set, use it for ChromeDriver.
    - Otherwise use Selenium's normal browser and driver discovery.
    - Never pause for keyboard input.

12. Generate API tests only for API cases identified in Jira.
    Generate TC-004 as a Karate API test using the configured endpoint,
    HTTP method, payload, and expected response fields.

13. Do not claim behavior that is unsupported by the supplied
    configuration. If genuinely required information is missing,
    report it in missing_details.

OUTPUT FORMAT
-------------
Return exactly one valid JSON object with these keys:
- ui_pytest: complete executable Python pytest source as a JSON string
- api_karate: complete Karate feature source as a JSON string
- missing_details: JSON array of strings

Return no Markdown fences and no explanatory text outside the JSON.

TEST REQUIREMENTS
-----------------
- Generate TC-001, TC-002, and TC-003 as executable Selenium tests.
- Generate TC-004 as a Karate API test.
- Include all imports, fixtures, and required test functions.
- Do not use pytest.mark.xfail or empty pass test bodies.
- Use the exact configured selectors, URLs, credentials, and messages.
- For TC-003, use the ID logout-button and verify the logged-out state.
- Return an empty missing_details array when the supplied
  configuration is sufficient for the four test cases.
"""

    system_prompt = """
You are a senior test automation engineer.

Generate complete, syntactically valid automation source code from
the supplied Jira test cases and application configuration.

Return exactly one valid JSON object containing:
ui_pytest, api_karate, and missing_details.

Python requirements:
- Use pytest and Selenium for UI tests.
- Include all required imports and a working browser fixture.
- Use explicit waits and meaningful assertions.
- Always close the browser in fixture teardown.
- Support CHROME_BIN and CHROMEDRIVER_PATH when configured.
- Do not force headless mode.
- Do not use input(), TODOs, empty tests, or placeholder failures.
- Do not skip requested test cases.
- Use dashboard visibility to confirm successful login.
- Use the exact logout selector By.ID, "logout-button".
- The configured logout selector is not missing.
- The TC-003 test must click logout and verify the logged-out state.

Karate requirements:
- Generate valid Karate feature syntax.
- Use only supplied API details.
- Verify the expected HTTP status and response fields.

Missing-information requirements:
- Report only information genuinely required but not supplied.
- Do not list configuration values that are already provided.
- Do not claim application behavior that is unsupported.

JSON requirements:
- Source code values must be valid JSON strings.
- Escape quotation marks, backslashes, and newline characters.
- Return no Markdown fences or explanatory text.
"""

    # Ask Groq to generate the scripts.
    raw_response = call_groq(system_prompt, prompt)
    result = parse_json_response(raw_response)

    # Validate the response structure.
    required_keys = (
        "ui_pytest",
        "api_karate",
        "missing_details",
    )

    for key in required_keys:
        if key not in result:
            raise ValueError(
                f"Groq response is missing the required key: {key}"
            )

    if not isinstance(result["missing_details"], list):
        raise ValueError("missing_details must be a JSON array.")

    # Normalize generated source code.
    result["ui_pytest"] = normalize_generated_code(
        result["ui_pytest"]
    )
    result["api_karate"] = normalize_generated_code(
        result["api_karate"]
    )

    ui_script = result["ui_pytest"]
    api_script = result["api_karate"]

    # Validate Python syntax.
    if not ui_script:
        raise ValueError("Groq generated an empty UI pytest script.")

    try:
        ast.parse(ui_script)
    except SyntaxError as exc:
        raise ValueError(
            f"Generated UI script has invalid Python syntax: {exc}"
        ) from exc

    # Validate the required UI test functions.
    required_ui_tests = (
        "test_tc_001_login_with_valid_credentials",
        "test_tc_002_login_with_invalid_credentials",
        "test_tc_003_logout_successfully",
    )

    for test_name in required_ui_tests:
        if not re.search(
            rf"^\s*def\s+{re.escape(test_name)}\s*\(",
            ui_script,
            flags=re.MULTILINE,
        ):
            raise ValueError(
                f"Generated UI script is missing {test_name}."
            )

    # Reject the known placeholder failure.
    if "Missing logout button selector" in ui_script:
        raise ValueError(
            "Generated UI script contains a missing-selector "
            "placeholder for TC-003. Regenerate the scripts."
        )

    # Ensure the logout test uses the configured selector.
    logout_match = re.search(
        r"def\s+test_tc_003_logout_successfully\s*\(.*?\):"
        r"(?P<body>.*?)(?=\n\s*def\s+|\Z)",
        ui_script,
        flags=re.DOTALL,
    )

    if not logout_match:
        raise ValueError("Could not locate the TC-003 logout test.")

    logout_body = logout_match.group("body")

    if "logout-button" not in logout_body:
        raise ValueError(
            "TC-003 does not use the configured logout-button ID."
        )

    if "pytest.fail(" in logout_body or "pytest.skip(" in logout_body:
        raise ValueError(
            "TC-003 contains a placeholder failure or skip."
        )

    # Validate the Karate feature.
    if not api_script or not re.search(
        r"^\s*Feature\s*:",
        api_script,
        flags=re.MULTILINE,
    ):
        raise ValueError(
            "Generated Karate script is empty or missing its "
            "Feature declaration."
        )

    return result

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


def generate_scripts(ticket):
    """Generate test artifacts from Jira and publish them to GitHub."""
    print("AI Test Generator Started")
    print("Issue:", ticket.get("issue_key"))
    print("Summary:", ticket.get("summary"))

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing from .env")

    issue_key = ticket.get("issue_key", "UNKNOWN")

    # Step 1: Extract test cases.
    extracted = extract_test_cases(ticket)
    test_cases = extracted["test_cases"]
    print("Test cases extracted:", len(test_cases))

    # Step 2: Generate automation source.
    generated = generate_automation_scripts(ticket, test_cases)

    # Step 3: Validate scripts before writing files.
    ui_script = generated["ui_pytest"]
    api_script = generated["api_karate"]

    if ui_script:
        try:
            ast.parse(ui_script)
        except SyntaxError as exc:
            print("\nGenerated Selenium script has invalid Python syntax.")
            print(f"Error: {exc}")
            print(f"Line: {exc.lineno}")
            print(f"Source: {exc.text}")
            raise

    if api_script and "Feature:" not in api_script:
        raise ValueError(
            "Generated Karate script is missing its Feature declaration."
        )

    # Step 4: Save generated artifacts.
    output_dir = Path("generated_tests") / issue_key
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "test_cases.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(extracted, file, indent=2, ensure_ascii=False)

    if ui_script:
        (output_dir / "test_ui.py").write_text(
            ui_script + "\n", encoding="utf-8"
        )

    if api_script:
        (output_dir / "test_api.feature").write_text(
            api_script + "\n", encoding="utf-8"
        )

    missing = generated["missing_details"]
    (output_dir / "missing_details.txt").write_text(
        "\n".join(str(item) for item in missing) + "\n",
        encoding="utf-8",
    )

    print("Generated test files in:", output_dir.resolve())

    if missing:
        print("Some details need to be configured:")
        for detail in missing:
            print("-", detail)

    # Step 5: Publish generated files.
    publish_result = publish_generated_tests(
        issue_key=issue_key,
        labels=ticket.get("labels", []),
        output_dir=output_dir,
        repo_dir=Path.cwd(),
        base_branch=os.getenv("GIT_BASE_BRANCH", "main"),
        summary=ticket.get("summary", ""),
    )

    print("Git publishing completed:", publish_result)
    print("Pull request URL:", publish_result.get("pr_url"))

    return {
        **generated,
        "git": publish_result,
    }


if __name__ == "__main__":
    from app.jira_reader import JiraReader

    print("Starting manual Jira test generation...")

    jira = JiraReader()
    ticket = jira.get_ticket("SCRUM-2")

    result = generate_scripts(ticket)

    print("Generation finished.")
    print(json.dumps(result, indent=2, ensure_ascii=False))
