
import os
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "http://127.0.0.1:8001/"

USERNAME = "testuser"
PASSWORD = "Password123"

INVALID_USERNAME = "invalid_user"
INVALID_PASSWORD = "WrongPassword123"

LOGIN_SUCCESS_MSG = "Login successful"
LOGIN_ERROR_MSG = "Invalid username or password"

DASHBOARD_TITLE = "Dashboard"
DASHBOARD_MESSAGE = "Welcome to the QA Demo Application"


@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")

    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    driver_path = os.getenv("CHROMEDRIVER_PATH")

    if driver_path:
        service = Service(executable_path=driver_path)
        wd = webdriver.Chrome(
            service=service,
            options=chrome_options
        )
    else:
        wd = webdriver.Chrome(options=chrome_options)

    yield wd
    wd.quit()


def perform_login(wd, username, password):
    wd.get(BASE_URL)
    wait = WebDriverWait(wd, 10)

    # Enter username.
    username_input = wait.until(
        EC.visibility_of_element_located((By.ID, "username"))
    )
    username_input.clear()
    username_input.send_keys(username)

    # Enter password.
    password_input = wd.find_element(By.ID, "password")
    password_input.clear()
    password_input.send_keys(password)

    # Submit login form.
    wd.find_element(By.ID, "login-button").click()

    # Successful login displays the dashboard and hides
    # the login section. Failed login leaves the login
    # section visible and displays an error message.
    def login_completed(driver):
        dashboard = driver.find_element(
            By.ID, "dashboard-title"
        )

        if dashboard.is_displayed():
            return "success"

        status = driver.find_element(
            By.ID, "login-status"
        )

        if status.is_displayed() and status.text.strip():
            return status.text.strip()

        return False

    outcome = wait.until(login_completed)

    if outcome == "success":
        return LOGIN_SUCCESS_MSG

    return outcome


def test_TC_001_login_with_valid_credentials(driver):
    status_text = perform_login(
        driver, USERNAME, PASSWORD
    )

    assert status_text == LOGIN_SUCCESS_MSG, (
        f"Expected '{LOGIN_SUCCESS_MSG}', "
        f"but got '{status_text}'"
    )

    wait = WebDriverWait(driver, 10)

    # Verify dashboard title.
    title_elem = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "dashboard-title")
        )
    )
    assert title_elem.text == DASHBOARD_TITLE

    # Verify dashboard message.
    message_elem = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "dashboard-message")
        )
    )
    assert message_elem.text == DASHBOARD_MESSAGE


def test_TC_002_login_with_invalid_credentials(driver):
    status_text = perform_login(
        driver,
        INVALID_USERNAME,
        INVALID_PASSWORD
    )

    assert status_text == LOGIN_ERROR_MSG, (
        f"Expected '{LOGIN_ERROR_MSG}', "
        f"but got '{status_text}'"
    )

    # Verify the login form remains visible.
    assert driver.find_element(
        By.ID, "login-section"
    ).is_displayed()

    # Verify the dashboard remains hidden.
    assert not driver.find_element(
        By.ID, "dashboard-section"
    ).is_displayed(), (
        "Dashboard should not be visible after failed login"
    )


def test_TC_003_logout_successfully(driver):
    status_text = perform_login(
        driver, USERNAME, PASSWORD
    )

    assert status_text == LOGIN_SUCCESS_MSG, (
        f"Login failed: {status_text}"
    )

    wait = WebDriverWait(driver, 10)

    # Verify dashboard is displayed after login.
    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "dashboard-title")
        )
    )

    # Click Logout.
    logout_button = wait.until(
        EC.element_to_be_clickable(
            (By.ID, "logout-button")
        )
    )
    logout_button.click()

    # Verify the login form is visible again.
    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "username")
        )
    )

    assert driver.find_element(
        By.ID, "password"
    ).is_displayed()

    # Verify dashboard is hidden after logout.
    assert not driver.find_element(
        By.ID, "dashboard-section"
    ).is_displayed(), (
        "Dashboard should not be visible after logout"
    )
