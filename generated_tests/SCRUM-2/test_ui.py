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
USERNAME_FIELD_ID = "username"
PASSWORD_FIELD_ID = "password"
LOGIN_BUTTON_ID = "login-button"

@pytest.fixture
def driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1920,1080")
    # Use custom Chrome binary if provided
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        chrome_options.binary_location = chrome_bin
    # Use custom ChromeDriver if provided
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = ChromeService(executable_path=driver_path)
        wd = webdriver.Chrome(service=service, options=chrome_options)
    else:
        wd = webdriver.Chrome(options=chrome_options)
    yield wd
    wd.quit()

def login(wd, username, password):
    wd.get(BASE_URL)
    WebDriverWait(wd, 10).until(EC.visibility_of_element_located((By.ID, USERNAME_FIELD_ID)))
    wd.find_element(By.ID, USERNAME_FIELD_ID).clear()
    wd.find_element(By.ID, USERNAME_FIELD_ID).send_keys(username)
    wd.find_element(By.ID, PASSWORD_FIELD_ID).clear()
    wd.find_element(By.ID, PASSWORD_FIELD_ID).send_keys(password)
    wd.find_element(By.ID, LOGIN_BUTTON_ID).click()

def test_tc_001_login_with_valid_credentials(driver):
    """TC-001: Login with valid credentials"""
    login(driver, USERNAME, PASSWORD)
    # Wait for dashboard title to become visible
    dashboard_title = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, DASHBOARD_TITLE_ID))
    )
    assert dashboard_title.text == "Dashboard"
    # Verify dashboard message
    dashboard_message = driver.find_element(By.ID, DASHBOARD_MESSAGE_ID)
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(driver):
    """TC-002: Login with invalid credentials"""
    login(driver, INVALID_USERNAME, INVALID_PASSWORD)
    # Wait for error message to be visible
    error_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, LOGIN_STATUS_ID))
    )
    assert error_elem.text == "Invalid username or password"
    # Ensure dashboard is not displayed
    WebDriverWait(driver, 5).until(
        EC.invisibility_of_element_located((By.ID, DASHBOARD_TITLE_ID))
    )

def test_tc_003_logout_successfully(driver):
    """TC-003: Logout successfully"""
    # First, log in with valid credentials
    login(driver, USERNAME, PASSWORD)
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, DASHBOARD_TITLE_ID))
    )
    # Locate logout button by its visible link text
    logout_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Logout"))
    )
    logout_button.click()
    # Verify that we are back on the login page (username field visible)
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, USERNAME_FIELD_ID))
    )
    # Verify dashboard is no longer visible
    WebDriverWait(driver, 5).until(
        EC.invisibility_of_element_located((By.ID, DASHBOARD_TITLE_ID))
    )
