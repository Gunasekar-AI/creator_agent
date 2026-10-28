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
        wd = webdriver.Chrome(service=service, options=chrome_options)
    else:
        wd = webdriver.Chrome(options=chrome_options)
    yield wd
    wd.quit()

def perform_login(wd, username, password):
    wd.get(BASE_URL)
    wait = WebDriverWait(wd, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).clear()
    wd.find_element(By.ID, "username").send_keys(username)
    wd.find_element(By.ID, "password").clear()
    wd.find_element(By.ID, "password").send_keys(password)
    wd.find_element(By.ID, "login-button").click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    return status_elem.text

def test_TC_001_login_with_valid_credentials(driver):
    status_text = perform_login(driver, USERNAME, PASSWORD)
    assert status_text == LOGIN_SUCCESS_MSG, f"Expected success message '{LOGIN_SUCCESS_MSG}', got '{status_text}'"
    wait = WebDriverWait(driver, 10)
    title_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.text == DASHBOARD_TITLE
    message_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message_elem.text == DASHBOARD_MESSAGE

def test_TC_002_login_with_invalid_credentials(driver):
    status_text = perform_login(driver, INVALID_USERNAME, INVALID_PASSWORD)
    assert status_text == LOGIN_ERROR_MSG, f"Expected error message '{LOGIN_ERROR_MSG}', got '{status_text}'"
    wait = WebDriverWait(driver, 5)
    dashboard_present = False
    try:
        wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
        dashboard_present = True
    except:
        dashboard_present = False
    assert not dashboard_present, "Dashboard should not be visible after failed login"

def test_TC_003_logout_successfully(driver):
    status_text = perform_login(driver, USERNAME, PASSWORD)
    assert status_text == LOGIN_SUCCESS_MSG
    LOGOUT_SELECTOR = None
    if not LOGOUT_SELECTOR:
        raise AssertionError("Logout button selector not provided for TC-003")
    # If selector were known, the steps would be:
    # driver.find_element(By.XPATH, LOGOUT_SELECTOR).click()
    # wait = WebDriverWait(driver, 10)
    # wait.until(EC.url_contains("login"))
    # assert "login" in driver.current_url.lower()
