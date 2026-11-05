import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

BASE_URL = "http://127.0.0.1:8001/"

@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    options.add_argument("window-size=1920,1080")
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        driver.quit()

def _get_credentials():
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    if not username or not password:
        raise RuntimeError("Environment variables TEST_USERNAME and TEST_PASSWORD must be set")
    return username, password

def test_tc_001_login_with_valid_credentials(browser):
    username, password = _get_credentials()
    browser.get(BASE_URL)
    wait = WebDriverWait(browser, 10)

    user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
    user_field.send_keys(username)
    pass_field.send_keys(password)

    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    login_btn.click()

    title_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.text == "Dashboard"

    message_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message_elem.text == "Welcome to the QA Demo Application"

    # Ensure login form is no longer visible
    wait.until(EC.invisibility_of_element_located((By.ID, "username")))
    wait.until(EC.invisibility_of_element_located((By.ID, "password")))
    wait.until(EC.invisibility_of_element_located((By.ID, "login-button")))

def test_tc_002_login_with_invalid_credentials(browser):
    browser.get(BASE_URL)
    wait = WebDriverWait(browser, 10)

    user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
    user_field.send_keys("invalid_user")
    pass_field.send_keys("WrongPassword123")

    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    login_btn.click()

    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"

    # Dashboard should not be displayed
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))

def test_tc_003_logout_successfully(browser):
    username, password = _get_credentials()
    browser.get(BASE_URL)
    wait = WebDriverWait(browser, 10)

    # Login steps
    user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    pass_field = wait.until(EC.visibility_of_element_located((By.ID, "password")))
    user_field.send_keys(username)
    pass_field.send_keys(password)

    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    login_btn.click()

    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))

    # Logout
    logout_btn = wait.until(EC.element_to_be_clickable((By.ID, "logout-button")))
    logout_btn.click()

    # Verify login form is visible again
    wait.until(EC.visibility_of_element_located((By.ID, "username")))
    # Verify dashboard is hidden
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))
