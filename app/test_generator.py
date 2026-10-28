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
    """Call Groq and return the model's text response."""
    client = get_groq_client()

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=8192,
        response_format={"type": "json_object"},
    )

    choice = response.choices[0]
    content = choice.message.content or ""

    print("\n--- GROQ RESPONSE DEBUG ---")
    print("Finish reason:", choice.finish_reason)
    print("Response content:")
    print(repr(content))
    print("--- END RESPONSE DEBUG ---\n")

    if choice.finish_reason == "length":
        raise RuntimeError(
            "Groq reached its completion-token limit. Reduce the requested "
            "output or use a model with a larger supported output limit."
        )

    if not content.strip():
        raise RuntimeError("Groq returned an empty response.")

    return content


def parse_json_response(response_text):
    """Parse JSON, including when the model wraps it in code fences."""
    cleaned = response_text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

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
    """
    Normalize source returned as a JSON string by the model.

    The outer response is decoded by json.loads(). Some model responses
    nevertheless contain an additional escaping layer (literal \\n and \\" ).
    Convert those only as needed, then validate the source before saving.
    """
    if not isinstance(code, str):
        return ""

    code = code.strip()
    if not code:
        return ""

    # If the source is still one line and contains escaped newline markers,
    # decode the extra escaping layer.
    if "\n" not in code and r"\n" in code:
        code = code.replace(r"\\n", "\n")
        code = code.replace(r"\n", "\n")
        code = code.replace(r"\r", "\r")

    # Escaped quotes can remain even when newline characters are already real.
    # Groq should return source code, not a second JSON-encoded string.
    code = code.replace(r'\"', '"')

    # Remove accidental Markdown fences if the model ignored the instruction.
    code = re.sub(r"^\s*```(?:python|gherkin|karate|feature)?\s*", "", code)
    code = re.sub(r"\s*```\s*$", "", code)

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
    """Generate UI and API automation from Jira test cases using Groq."""
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
The following configuration is provided for the QA demo application.

UI base URL: http://127.0.0.1:8001/
Username field ID: username
Password field ID: password
Login button ID: login-button
Login status element ID: login-status
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
success=true, message="Login successful", username="testuser"

GENERATION RULES
----------------
1. Jira description and extracted test cases determine which tests
   must be generated. Do not omit a case merely because its title
   mentions logout or another authentication operation.

2. Generate Selenium pytest tests for UI cases and Karate feature
   scenarios for API cases.

3. Preserve Jira test case IDs and cover each case with an appropriate
   automated test.

4. Generate executable code, not pseudocode, placeholders, or TODOs.

5. Use the application configuration above where it applies.
   Do not invent URLs, API endpoints, credentials, element IDs,
   success messages, or backend behavior.

6. For UI tests, use Selenium explicit waits and meaningful assertions.
   Verify both expected success and expected failure behavior.

7. For logout tests:
   - First log in with valid credentials if required.
   - Use the logout control described by Jira and locate it using
     an appropriate accessible name or visible text when possible.
   - Click the control and wait for the expected redirect.
   - Verify the logged-out state and that protected content is no
     longer accessible, where specified by the application.
   - Never call pytest.skip merely because the case is about logout.
   - Do not assume logout works if the application does not implement it.
   - If a required selector, route, or behavior is not specified and
     cannot be established from the supplied configuration, report it
     in missing_details rather than inventing implementation details.

8. For invalid login, verify the specified error message and ensure
   the dashboard is not displayed.

9. Use a pytest fixture that always closes the browser in teardown.
   Do not pause for keyboard input.

10. Support both local Windows execution and GitHub Actions:
    - Do not force headless mode.
    - Use a 1920x1080 browser window.
    - If CHROME_BIN is set, use it as the Chrome binary.
    - If CHROMEDRIVER_PATH is set, use it as the ChromeDriver service.
    - If these environment variables are absent, allow Selenium to
      use its normal local browser/driver discovery.

11. Generate API tests only for API cases identified in Jira.
    Use the supplied API configuration where applicable.
    Do not invent additional endpoints or response fields.

12. Do not silently omit test cases. If a case cannot be automated
    with the supplied information, document the exact missing
    information in missing_details.

OUTPUT FORMAT
-------------
Return exactly one valid JSON object with these keys:
- ui_pytest: string containing executable Python pytest source
- api_karate: string containing a Karate feature file
- missing_details: array of strings

Return no Markdown fences or explanatory text outside the JSON.
"""

    system_prompt = """
You are a senior test automation engineer.

Treat the Jira description and extracted test cases as the source
of truth for the requested test coverage.

Generate complete, syntactically valid automation scripts.
Do not automatically skip a requested test case.
Do not fabricate application functionality, selectors, endpoints,
credentials, or expected results.

Python:
- Use pytest and Selenium for UI tests.
- Include the imports and fixtures required by the generated tests.
- Use Selenium explicit waits.
- Use normal Python syntax and meaningful assertions.
- Use unique, descriptive test function names.
- Ensure browser teardown happens even when a test fails.
- Use environment-configured Chrome and ChromeDriver when available.
- Never use input() to pause a test.
- Do not use headless mode unless the supplied requirements explicitly
  request it.
- Do not assert that an element is absent by expecting a timeout
  from presence_of_element_located. Use appropriate visibility checks.

Karate:
- Generate valid Karate feature syntax.
- Use only API details supplied in the configuration or Jira.
- Verify the status and response fields specified by the test case.

Missing information:
- Return missing_details for required application details that cannot
  be established from the supplied information.
- Do not list configuration values already provided as missing.
- Do not claim a requested behavior is implemented without evidence.

Return exactly one JSON object containing ui_pytest, api_karate,
and missing_details. Source code values must be JSON strings.
"""

    result = parse_json_response(
        call_groq(system_prompt, prompt)
    )

    for key in ("ui_pytest", "api_karate", "missing_details"):
        if key not in result:
            raise ValueError(
                f"Groq response is missing the required key: {key}"
            )

    if not isinstance(result["missing_details"], list):
        raise ValueError("missing_details must be a JSON array.")

    result["ui_pytest"] = normalize_generated_code(
        result["ui_pytest"]
    )
    result["api_karate"] = normalize_generated_code(
        result["api_karate"]
    )

    if result["ui_pytest"]:
        ast.parse(result["ui_pytest"])

    if result["api_karate"] and "Feature:" not in result["api_karate"]:
        raise ValueError(
            "Generated Karate script is missing its Feature declaration."
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
