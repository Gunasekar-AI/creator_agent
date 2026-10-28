
import os

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


BASE_URL = "http://127.0.0.1:8001/"

USERNAME = "testuser"
PASSWORD = "Password123"

INVALID_USERNAME = "invalid_user"
INVALID_PASSWORD = "WrongPassword123"

LOGIN_STATUS_ID = "login-status"
DASHBOARD_TITLE_ID = "dashboard-title"
DASHBOARD_MESSAGE_ID = "dashboard-message"
DASHBOARD_SECTION_ID = "dashboard-section"

USERNAME_FIELD_ID = "username"
PASSWORD_FIELD_ID = "password"
LOGIN_BUTTON_ID = "login-button"
LOGOUT_BUTTON_ID = "logout-button"


@pytest.fixture
def driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Use a custom Chrome binary if provided.
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        chrome_options.binary_location = chrome_bin

    # Use a custom ChromeDriver if provided.
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = ChromeService(executable_path=driver_path)
        wd = webdriver.Chrome(service=service, options=chrome_options)
    else:
        wd = webdriver.Chrome(options=chrome_options)

    yield wd
    wd.quit()


def login(wd, username, password):
    """Open the app and submit the supplied login credentials."""
    wd.get(BASE_URL)

    wait = WebDriverWait(wd, 10)

    username_field = wait.until(
        EC.visibility_of_element_located(
            (By.ID, USERNAME_FIELD_ID)
        )
    )
    username_field.clear()
    username_field.send_keys(username)

    password_field = wd.find_element(By.ID, PASSWORD_FIELD_ID)
    password_field.clear()
    password_field.send_keys(password)

    wd.find_element(By.ID, LOGIN_BUTTON_ID).click()


def test_tc_001_login_with_valid_credentials(driver):
    """TC-001: Login with valid credentials."""
    login(driver, USERNAME, PASSWORD)

    wait = WebDriverWait(driver, 10)

    dashboard_title = wait.until(
        EC.visibility_of_element_located(
            (By.ID, DASHBOARD_TITLE_ID)
        )
    )

    assert dashboard_title.text.strip() == "Dashboard"

    dashboard_message = wait.until(
        EC.visibility_of_element_located(
            (By.ID, DASHBOARD_MESSAGE_ID)
        )
    )

    assert (
        dashboard_message.text.strip()
        == "Welcome to the QA Demo Application"
    )


def test_tc_002_login_with_invalid_credentials(driver):
    """TC-002: Login with invalid credentials."""
    login(driver, INVALID_USERNAME, INVALID_PASSWORD)

    wait = WebDriverWait(driver, 10)

    error_element = wait.until(
        EC.visibility_of_element_located(
            (By.ID, LOGIN_STATUS_ID)
        )
    )

    assert (
        error_element.text.strip()
        == "Invalid username or password"
    )

    # The dashboard must remain hidden after invalid login.
    assert not driver.find_element(
        By.ID, DASHBOARD_SECTION_ID
    ).is_displayed()


def test_tc_003_logout_successfully(driver):
    """TC-003: Log in successfully and then log out."""
    login(driver, USERNAME, PASSWORD)

    wait = WebDriverWait(driver, 10)

    # Wait until login has succeeded and the dashboard is visible.
    dashboard_title = wait.until(
        EC.visibility_of_element_located(
            (By.ID, DASHBOARD_TITLE_ID)
        )
    )

    assert dashboard_title.text.strip() == "Dashboard"

    # Find the actual logout button by its HTML ID.
    logout_button = wait.until(
        EC.element_to_be_clickable(
            (By.ID, LOGOUT_BUTTON_ID)
        )
    )

    logout_button.click()

    # Verify that the login form is visible again.
    wait.until(
        EC.visibility_of_element_located(
            (By.ID, USERNAME_FIELD_ID)
        )
    )

    wait.until(
        EC.visibility_of_element_located(
            (By.ID, LOGIN_BUTTON_ID)
        )
    )

    # Verify that the dashboard is hidden after logout.
    assert not driver.find_element(
        By.ID, DASHBOARD_SECTION_ID
    ).is_displayed()
