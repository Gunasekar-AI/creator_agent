import ast
import json
import os
import re
from pathlib import Path

import pytest
from selenium import webdriver

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
    """Generate Selenium pytest and Karate scripts from extracted cases."""
    description = jira_description_to_text(ticket.get("description"))

  
    prompt = f"""
JIRA TICKET
-----------
Issue: {ticket.get('issue_key')}
Summary: {ticket.get('summary')}
Description:
{description}

APPLICATION CONFIGURATION
-------------------------
This project uses the local QA demo application.

UI:
- Login page URL: http://127.0.0.1:8001/
- Username field ID: username
- Password field ID: password
- Login button ID: login-button
- Login status element ID: login-status
- Dashboard title element ID: dashboard-title
- Dashboard message element ID: dashboard-message
- Valid username: testuser
- Valid password: Password123
- Invalid username: invalid_user
- Invalid password: WrongPassword123
- Invalid credentials message: Invalid username or password
- Successful login message: Login successful
- Dashboard title: Dashboard
- Dashboard message: Welcome to the QA Demo Application
- The application does not implement logout. Skip the logout test
  with pytest.skip rather than inventing a logout button.

API:
- Login endpoint: http://127.0.0.1:8001/api/login
- Method: POST
- JSON request body:
  {{"username": "testuser", "password": "Password123"}}
- Expected successful response fields:
  success, message, username
- Expected successful values:
  success=true, message="Login successful", username="testuser"

TEST CASES
----------
{json.dumps(test_cases, indent=2)}

OUTPUT REQUIREMENTS
-------------------
Return one valid JSON object with exactly these keys:
- ui_pytest: string containing executable Python pytest source
- api_karate: string containing a Karate feature
- missing_details: array of strings


For local Windows execution:
- Do not use headless mode.
- Create a webdriver.ChromeOptions() object.
- Add options.add_argument("--window-size=1920,1080").
- Create the driver using webdriver.Chrome(options=options).
- Do not call driver.maximize_window().
- Do not use input() to pause the browser.
- Always call driver.quit() during fixture teardown.
- Keep the generated test fixture compatible with GitHub Actions.


Requirements:
1. Use the exact application URLs, element IDs, credentials and messages
   specified above. Never replace them with TODO placeholders.
2. Use Selenium explicit waits.
3. For valid login, verify the success message and dashboard elements.
4. For invalid login, verify the exact error message and that the
   dashboard is not displayed.
5. For logout, use pytest.skip because logout is not implemented.
6. Use the API endpoint and JSON payload specified above.
7. In Karate, verify status 200 and the success, message and username
   response fields.
8. Do not enable headless mode. Chrome must open visibly when tests are
   run locally on Windows. CI may provide a virtual display if needed.
9. Do not invent endpoints, selectors, or application behavior.
10. Return an empty missing_details array for details supplied above.
11. Return no Markdown fences or explanatory prose.
"""

    system_prompt = """
You are an experienced test automation engineer.

For invalid-login tests, verify the dashboard is not visible using
Selenium's is_displayed(). Do not use presence_of_element_located()
with pytest.raises(TimeoutException) to assert that the dashboard
is absent or hidden.
For invalid-login UI tests, verify that the dashboard is not visible
using Selenium's is_displayed(). Do not use
pytest.raises(TimeoutException) with presence_of_element_located()
to verify that the dashboard is hidden.
Return exactly one valid JSON object.
The object must contain ui_pytest, api_karate, and missing_details.

The source code fields must be JSON strings with correctly escaped
quotes, backslashes, and newlines.

Python requirements:
- Generate syntactically valid Python.
- Use Selenium and pytest for UI cases.
- Use underscores in function and variable names.
- Use normal Python attribute and method access.
- Include assertions for the expected behavior where possible.
- Do not invent application details.
- Do not truncate functions or statements.
Use the APPLICATION CONFIGURATION in the user prompt as the
source of truth. Never replace supplied values with TODO placeholders.
Do not report supplied configuration values as missing.
Generate tests only for behavior supported by the supplied configuration.

Karate requirements:
- Generate valid Karate feature syntax.
- Do not invent API contract details.

For local Windows execution:
- Do not use headless mode.
- Use webdriver.Chrome() and maximize the browser window.
- In the pytest fixture teardown, wait for the user to press Enter
  before calling driver.quit().
- Use input("Press Enter to close Chrome...") for this pause.

Keep the response concise. Do not repeat the test-case list.
Do not return Markdown fences or text outside the JSON object.
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
