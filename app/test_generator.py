import os
import json
import re
from pathlib import Path
import ast
from dotenv import load_dotenv
from groq import Groq
from app.git_publisher import publish_generated_tests

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def jira_description_to_text(value):
    """Convert Jira description, including Atlassian rich-text content, to text."""

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "\n".join(
            jira_description_to_text(item)
            for item in value
        )

    if isinstance(value, dict):
        # Jira rich-text nodes often store text in "text"
        if value.get("type") == "text":
            return value.get("text", "")

        content = value.get("content", [])

        if content:
            return jira_description_to_text(content)

        return value.get("text", "")

    return str(value)


def call_groq(system_prompt, user_prompt):
    """Call Groq and return the model's text response."""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0.1,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        max_tokens=4000,
        response_format={"type": "json_object"},
    )

    choice = response.choices[0]

    # Temporary debugging: inspect the model response
    print("\n--- GROQ RESPONSE DEBUG ---")
    print("Finish reason:", choice.finish_reason)
    print("Response content:")
    print(repr(choice.message.content))
    print("--- END RESPONSE DEBUG ---\n")

    return choice.message.content

def parse_json_response(response_text):
    """Parse JSON, including when the model wraps it in a code fence."""

    cleaned = response_text.strip()

    # Remove optional Markdown code fences
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    return json.loads(cleaned)


def extract_test_cases(ticket):
    """Use Groq to extract structured test cases from the Jira ticket."""

    description = jira_description_to_text(
        ticket.get("description")
    )

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
- If a test case does not specify a detail, use null or an empty
  value and list the missing information in "missing_details".
- Classify each case as "ui", "api", or "other".
- Return valid JSON only, with this structure:

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

    response = call_groq(system_prompt, ticket_text)
    result = parse_json_response(response)

    if not isinstance(result.get("test_cases"), list):
        raise ValueError("Groq did not return a test_cases list")

    return result


def generate_automation_scripts(ticket, test_cases):
    """Generate Selenium pytest and Karate scripts from extracted cases."""

    description = jira_description_to_text(
        ticket.get("description")
    )

    prompt = f"""
JIRA TICKET
-----------
Issue: {ticket.get('issue_key')}
Summary: {ticket.get('summary')}
Description:
{description}

EXTRACTED TEST CASES
---------------------
{json.dumps(test_cases, indent=2)}

Generate automation scripts based on the ticket and extracted
test cases.

Requirements:

1. UI tests:
   - Use Python Selenium and pytest.
   - Use the UI test cases only.
   - Use explicit waits where appropriate.
   - Do not invent application URLs, locators, or credentials.
   - If a locator or URL is missing, clearly mark it as a
     TODO placeholder and explain it in missing_details.

2. API tests:
   - Use Karate .feature syntax.
   - Use API test cases only.
   - Do not invent endpoints, request payloads, or authentication.
   - If an endpoint or required payload is missing, mark it
     as a TODO placeholder and explain it in missing_details.

3. Do not include test cases that are classified as "other".

4. Return valid JSON only, with this structure:

{{
  "ui_pytest": "complete Python pytest source code",
  "api_karate": "complete Karate feature source code",
  "missing_details": [
    "Details needed before the scripts can run"
  ]
}}

Return empty strings for a script type that has no applicable
test cases. Do not wrap the JSON in Markdown fences.
"""

    system_prompt = """
You are an experienced test automation engineer.

Generate valid, complete, executable source code for Selenium
pytest tests and Karate API tests.

CRITICAL PYTHON RULES:
- Preserve Python syntax exactly.
- Use underscores in Python function and variable names.
- Use dots for Python attribute and method access.
- Examples:
  driver.maximize_window()
  EC.visibility_of_element_located(...)
  username_field.send_keys(...)
  def test_login_valid_credentials(...):
- Never replace underscores or dots with asterisks.
- Do not use Markdown code fences.
- Do not return literal backslash-n sequences as line breaks
  inside the source code strings.
- Return complete functions and statements; never truncate.

CRITICAL OUTPUT RULES:
- Return one valid JSON object only.
- The JSON object must contain ui_pytest, api_karate,
  and missing_details.
- ui_pytest and api_karate must be strings containing source code.
- Escape the source code correctly as JSON strings.
- Do not invent application URLs, selectors, credentials,
  endpoints, request bodies, or expected results.
"""
    response = call_groq(system_prompt, prompt)
    return parse_json_response(response)


def generate_scripts(ticket):
    """Main entry point called by the Jira webhook."""

    print("AI Test Generator Started")
    print("Issue:", ticket.get("issue_key"))
    print("Summary:", ticket.get("summary"))

    if not os.getenv("GROQ_API_KEY"):
        raise ValueError("GROQ_API_KEY is missing from .env")

    # Step 1: Extract test cases from Jira using Groq
    extracted = extract_test_cases(ticket)
    test_cases = extracted["test_cases"]

    print("Test cases extracted:", len(test_cases))

    # Step 2: Generate UI and API automation scripts
    generated = generate_automation_scripts(
        ticket,
        test_cases,
    )

    # Step 3: Save files
    issue_key = ticket.get("issue_key", "UNKNOWN")
    output_dir = Path("generated_tests") / issue_key
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save extracted test cases for traceability
    with open(
        output_dir / "test_cases.json",
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            extracted,
            file,
            indent=2,
            ensure_ascii=False,
        )

    # Save Selenium tests
    ui_script = generated.get("ui_pytest", "").strip()
    if ui_script:
        try:
            ast.parse(ui_script)
        except SyntaxError as e:
            print("\nGenerated Selenium script has invalid Python syntax.")
            print(f"Error: {e}")
            print(f"Line: {e.lineno}")
            print(f"Source: {e.text}")
            raise

    if ui_script:
        with open(
            output_dir / "test_ui.py",
            "w",
            encoding="utf-8",
        ) as file:
            file.write(ui_script)

    # Save Karate tests
    api_script = generated.get("api_karate", "").strip()

    if api_script:
        with open(
            output_dir / "test_api.feature",
            "w",
            encoding="utf-8",
        ) as file:
            file.write(api_script)

    # Save missing configuration/details
    missing = generated.get("missing_details", [])

    with open(
        output_dir / "missing_details.txt",
        "w",
        encoding="utf-8",
    ) as file:
        file.write("\n".join(missing))

    print("Generated test files in:", output_dir.resolve())

    if missing:
        print("Some details need to be configured:")
        for detail in missing:
            print("-", detail)
        # Step 4: Create a branch, commit generated tests, and push.
    publish_result = publish_generated_tests(
        issue_key=issue_key,
        labels=ticket.get("labels", []),
        output_dir=output_dir,
        repo_dir=Path.cwd(),
        base_branch=os.getenv("GIT_BASE_BRANCH", "main"),
    )

    print("Git publishing completed:", publish_result)

    return generated


if __name__ == "__main__":
    from app.jira_reader import JiraReader

    print("Starting manual Jira test generation...")

    jira = JiraReader()
    ticket = jira.get_ticket("SCRUM-2")

    result = generate_scripts(ticket)

    print("Generation finished.")
    print(result)