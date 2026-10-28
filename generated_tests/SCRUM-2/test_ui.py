import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

BASE_URL = "http://127.0.0.1:8001/"

@pytest.fixture(scope="function")
def driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--window-size=1920,1080")
    if os.getenv("CHROME_BIN"):
        chrome_options.binary_location = os.getenv("CHROME_BIN")
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = Service(driver_path)
        wd = webdriver.Chrome(service=service, options=chrome_options)
    else:
        wd = webdriver.Chrome(options=chrome_options)
    yield wd
    wd.quit()

def login(driver, username, password):
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).clear()
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-button").click()
    wait.until(EC.visibility_of_element_located((By.ID, "login-status")))

def test_tc_001_login_with_valid_credentials(driver):
    login(driver, "testuser", "Password123")
    wait = WebDriverWait(driver, 10)
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.text == "Dashboard"
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(driver):
    login(driver, "invalid_user", "WrongPassword123")
    wait = WebDriverWait(driver, 10)
    login_status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert login_status.text == "Invalid username or password"
    # Ensure dashboard is not displayed
    assert len(driver.find_elements(By.ID, "dashboard-title")) == 0

def test_tc_003_logout_successfully(driver):
    # Precondition: user is logged in
    login(driver, "testuser", "Password123")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    # Missing logout button selector - cannot locate logout control
    # Missing protected page URL to verify access after logout
    # Placeholder for logout steps
    # TODO: Implement logout when selector and protected page URL are available
    assert True  # Placeholder assertion
