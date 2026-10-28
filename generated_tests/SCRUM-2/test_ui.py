import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuration constants
BASE_URL = "http://127.0.0.1:8001/"
USERNAME_ID = "username"
PASSWORD_ID = "password"
LOGIN_BUTTON_ID = "login-button"
LOGIN_STATUS_ID = "login-status"
DASHBOARD_TITLE_ID = "dashboard-title"
DASHBOARD_MESSAGE_ID = "dashboard-message"

VALID_USERNAME = "testuser"
VALID_PASSWORD = "Password123"
INVALID_USERNAME = "invalid_user"
INVALID_PASSWORD = "WrongPassword123"

INVALID_LOGIN_MESSAGE = "Invalid username or password"
SUCCESSFUL_LOGIN_MESSAGE = "Login successful"
DASHBOARD_TITLE_TEXT = "Dashboard"
DASHBOARD_MESSAGE_TEXT = "Welcome to the QA Demo Application"

# Placeholder for logout button selector – missing from configuration
LOGOUT_BUTTON_SELECTOR = None

@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    # Use environment variables if provided
    chrome_binary = os.getenv("CHROME_BIN")
    if chrome_binary:
        chrome_options.binary_location = chrome_binary
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = ChromeService(executable_path=driver_path)
        _driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        _driver = webdriver.Chrome(options=chrome_options)
    yield _driver
    try:
        _driver.quit()
    except Exception:
        pass

def login(driver, username, password):
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, USERNAME_ID)))
    driver.find_element(By.ID, USERNAME_ID).clear()
    driver.find_element(By.ID, USERNAME_ID).send_keys(username)
    driver.find_element(By.ID, PASSWORD_ID).clear()
    driver.find_element(By.ID, PASSWORD_ID).send_keys(password)
    driver.find_element(By.ID, LOGIN_BUTTON_ID).click()

def wait_for_dashboard(driver):
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, DASHBOARD_TITLE_ID)))
    wait.until(EC.visibility_of_element_located((By.ID, DASHBOARD_MESSAGE_ID)))

def wait_for_login_status(driver):
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, LOGIN_STATUS_ID)))

def is_element_visible(driver, by, locator):
    try:
        WebDriverWait(driver, 5).until(EC.visibility_of_element_located((by, locator)))
        return True
    except Exception:
        return False

def test_tc_001_login_with_valid_credentials(driver):
    """TC-001: Login with valid credentials"""
    login(driver, VALID_USERNAME, VALID_PASSWORD)
    wait_for_dashboard(driver)
    title_text = driver.find_element(By.ID, DASHBOARD_TITLE_ID).text
    message_text = driver.find_element(By.ID, DASHBOARD_MESSAGE_ID).text
    assert title_text == DASHBOARD_TITLE_TEXT, f"Expected dashboard title '{DASHBOARD_TITLE_TEXT}', got '{title_text}'"
    assert message_text == DASHBOARD_MESSAGE_TEXT, f"Expected dashboard message '{DASHBOARD_MESSAGE_TEXT}', got '{message_text}'"
    # Optionally verify login status element is hidden after successful login
    assert not is_element_visible(driver, By.ID, LOGIN_STATUS_ID), "Login status element should be hidden after successful login"

def test_tc_002_login_with_invalid_credentials(driver):
    """TC-002: Login with invalid credentials"""
    login(driver, INVALID_USERNAME, INVALID_PASSWORD)
    wait_for_login_status(driver)
    status_text = driver.find_element(By.ID, LOGIN_STATUS_ID).text
    assert status_text == INVALID_LOGIN_MESSAGE, f"Expected error message '{INVALID_LOGIN_MESSAGE}', got '{status_text}'"
    # Dashboard should not be visible
    assert not is_element_visible(driver, By.ID, DASHBOARD_TITLE_ID), "Dashboard title should not be visible after failed login"
    assert not is_element_visible(driver, By.ID, DASHBOARD_MESSAGE_ID), "Dashboard message should not be visible after failed login"

def test_tc_003_logout_successfully(driver):
    """TC-003: Logout successfully"""
    # Precondition: user is logged in
    login(driver, VALID_USERNAME, VALID_PASSWORD)
    wait_for_dashboard(driver)
    # Verify we have a selector for the logout button
    if not LOGOUT_BUTTON_SELECTOR:
        pytest.fail("Missing logout button selector – cannot perform logout step")
    # Perform logout
    driver.find_element(*LOGOUT_BUTTON_SELECTOR).click()
    # After logout, login form should be visible again and dashboard hidden
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, USERNAME_ID)))
    assert is_element_visible(driver, By.ID, USERNAME_ID), "Username field should be visible after logout"
    assert not is_element_visible(driver, By.ID, DASHBOARD_TITLE_ID), "Dashboard title should be hidden after logout"
    assert not is_element_visible(driver, By.ID, DASHBOARD_MESSAGE_ID), "Dashboard message should be hidden after logout"
