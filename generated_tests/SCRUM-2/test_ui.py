import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://127.0.0.1:8001/"
USERNAME = "testuser"
PASSWORD = "Password123"
INVALID_USERNAME = "invalid_user"
INVALID_PASSWORD = "WrongPassword123"
LOGIN_STATUS_ID = "login-status"
DASHBOARD_TITLE_ID = "dashboard-title"
SUCCESS_MESSAGE = "Login successful"
ERROR_MESSAGE = "Invalid username or password"

@pytest.fixture
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = ChromeService(executable_path=driver_path)
        wd = webdriver.Chrome(service=service, options=options)
    else:
        wd = webdriver.Chrome(options=options)
    yield wd
    wd.quit()

def login(wd, username, password):
    wd.get(BASE_URL)
    wait = WebDriverWait(wd, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).clear()
    wd.find_element(By.ID, "username").send_keys(username)
    wd.find_element(By.ID, "password").clear()
    wd.find_element(By.ID, "password").send_keys(password)
    wd.find_element(By.ID, "login-button").click()

def test_tc_001_login_with_valid_credentials(driver):
    login(driver, USERNAME, PASSWORD)
    wait = WebDriverWait(driver, 10)
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, LOGIN_STATUS_ID)))
    assert status_elem.text == SUCCESS_MESSAGE
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, DASHBOARD_TITLE_ID)))
    assert dashboard_title.text == "Dashboard"

def test_tc_002_login_with_invalid_credentials(driver):
    login(driver, INVALID_USERNAME, INVALID_PASSWORD)
    wait = WebDriverWait(driver, 10)
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, LOGIN_STATUS_ID)))
    assert status_elem.text == ERROR_MESSAGE
    # Ensure dashboard is not displayed
    dashboard_elements = driver.find_elements(By.ID, DASHBOARD_TITLE_ID)
    assert len(dashboard_elements) == 0

def test_tc_003_logout_successfully(driver):
    # Precondition: user is logged in
    login(driver, USERNAME, PASSWORD)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, DASHBOARD_TITLE_ID)))
    # Click logout - selector not provided
    # Missing selector for logout button
    raise NotImplementedError("Logout button selector is missing. Cannot locate logout control.")
    # After logout, verify redirected to login page and session cleared
    # Additional steps would be implemented once selector and protected page URL are known.
