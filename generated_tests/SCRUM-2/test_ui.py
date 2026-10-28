import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
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

SUCCESS_MESSAGE = "Login successful"
INVALID_MESSAGE = "Invalid username or password"
DASHBOARD_TITLE = "Dashboard"
DASHBOARD_MESSAGE = "Welcome to the QA Demo Application"

@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    if os.getenv("CHROME_BIN"):
        chrome_options.binary_location = os.getenv("CHROME_BIN")
    service = None
    if os.getenv("CHROMEDRIVER_PATH"):
        service = Service(os.getenv("CHROMEDRIVER_PATH"))
    driver = webdriver.Chrome(service=service, options=chrome_options)
    yield driver
    driver.quit()

def wait_for_element(driver, by, locator, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, locator))
    )

def test_tc_001_login_with_valid_credentials(driver):
    driver.get(BASE_URL)
    wait_for_element(driver, By.ID, USERNAME_ID).send_keys(VALID_USERNAME)
    wait_for_element(driver, By.ID, PASSWORD_ID).send_keys(VALID_PASSWORD)
    wait_for_element(driver, By.ID, LOGIN_BUTTON_ID).click()
    # Verify dashboard appears
    title_elem = wait_for_element(driver, By.ID, DASHBOARD_TITLE_ID)
    assert title_elem.text == DASHBOARD_TITLE
    # Verify success message
    status_elem = wait_for_element(driver, By.ID, LOGIN_STATUS_ID)
    assert status_elem.text == SUCCESS_MESSAGE

def test_tc_002_login_with_invalid_credentials(driver):
    driver.get(BASE_URL)
    wait_for_element(driver, By.ID, USERNAME_ID).send_keys(INVALID_USERNAME)
    wait_for_element(driver, By.ID, PASSWORD_ID).send_keys(INVALID_PASSWORD)
    wait_for_element(driver, By.ID, LOGIN_BUTTON_ID).click()
    status_elem = wait_for_element(driver, By.ID, LOGIN_STATUS_ID)
    assert status_elem.text == INVALID_MESSAGE
    # Ensure dashboard is not displayed
    dashboard_elements = driver.find_elements(By.ID, DASHBOARD_TITLE_ID)
    assert len(dashboard_elements) == 0

def test_tc_003_logout_successfully(driver):
    # Step 1: Log in with valid credentials
    driver.get(BASE_URL)
    wait_for_element(driver, By.ID, USERNAME_ID).send_keys(VALID_USERNAME)
    wait_for_element(driver, By.ID, PASSWORD_ID).send_keys(VALID_PASSWORD)
    wait_for_element(driver, By.ID, LOGIN_BUTTON_ID).click()
    wait_for_element(driver, By.ID, DASHBOARD_TITLE_ID)
    # Step 2: Click the Logout button (identified by visible text)
    logout_button = wait_for_element(driver, By.XPATH, "//button[normalize-space()='Logout']")
    logout_button.click()
    # Step 3: Verify redirect to login page
    wait_for_element(driver, By.ID, LOGIN_BUTTON_ID)
    assert driver.current_url.rstrip('/') == BASE_URL.rstrip('/')
    # Step 4: Verify protected content is no longer accessible
    dashboard_elements = driver.find_elements(By.ID, DASHBOARD_TITLE_ID)
    assert len(dashboard_elements) == 0
