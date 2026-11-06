import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

@pytest.fixture(scope="function")
def browser():
    options = webdriver.ChromeOptions()
    chrome_bin = os.getenv('CHROME_BIN')
    if chrome_bin:
        options.binary_location = chrome_bin
    options.add_argument('window-size=1920,1080')
    driver_path = os.getenv('CHROMEDRIVER_PATH')
    try:
        if driver_path:
            from selenium.webdriver.chrome.service import Service
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        yield driver
    finally:
        try:
            driver.quit()
        except Exception:
            pass

BASE_URL = "http://127.0.0.1:8001/"

def _get_valid_credentials():
    username = os.getenv('TEST_USERNAME')
    password = os.getenv('TEST_PASSWORD')
    if not username or not password:
        raise RuntimeError('Missing TEST_USERNAME or TEST_PASSWORD environment variable')
    return username, password

def test_tc_001_login_with_valid_credentials(browser):
    username, password = _get_valid_credentials()
    browser.get(BASE_URL)
    browser.find_element(By.ID, "username").send_keys(username)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.ID, "login-button").click()
    # Wait for dashboard title
    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-title"))
    )
    title = browser.find_element(By.ID, "dashboard-title").text
    message = browser.find_element(By.ID, "dashboard-message").text
    assert title == "Dashboard"
    assert message == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(browser):
    invalid_user = "invalid_user"
    invalid_pass = "WrongPassword123"
    browser.get(BASE_URL)
    browser.find_element(By.ID, "username").send_keys(invalid_user)
    browser.find_element(By.ID, "password").send_keys(invalid_pass)
    browser.find_element(By.ID, "login-button").click()
    # Wait for error status
    error_elem = WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )
    assert error_elem.text == "Invalid username or password"
    # Dashboard section should be hidden or absent
    sections = browser.find_elements(By.ID, "dashboard-section")
    if sections:
        assert not sections[0].is_displayed()

def test_tc_003_logout_successfully(browser):
    username, password = _get_valid_credentials()
    browser.get(BASE_URL)
    browser.find_element(By.ID, "username").send_keys(username)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.ID, "login-button").click()
    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-title"))
    )
    # Perform logout
    browser.find_element(By.ID, "logout-button").click()
    # Wait for login page to reappear
    WebDriverWait(browser, 10).until(
        EC.visibility_of_element_located((By.ID, "username"))
    )
    # Verify dashboard is hidden
    sections = browser.find_elements(By.ID, "dashboard-section")
    if sections:
        assert not sections[0].is_displayed()
