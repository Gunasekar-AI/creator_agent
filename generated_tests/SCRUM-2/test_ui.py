import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def browser():
    options = Options()
    options.add_argument("window-size=1920,1080")
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
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

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001")
USERNAME = os.getenv("TEST_USERNAME")
PASSWORD = os.getenv("TEST_PASSWORD")

def test_tc_001_login_with_valid_credentials(browser):
    driver = browser
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    # Verify successful login
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    title = driver.find_element(By.ID, "dashboard-title").text
    message = driver.find_element(By.ID, "dashboard-message").text
    assert title == "Dashboard"
    assert message == "Welcome to the QA Demo Application"
    status = driver.find_element(By.ID, "login-status").text
    assert "Login successful" in status

def test_tc_002_login_with_invalid_credentials(browser):
    driver = browser
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("invalid_pass")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    # Verify error message
    error = wait.until(EC.visibility_of_element_located((By.ID, "login-status"))).text
    assert "Invalid username or password" in error

def test_tc_003_logout_successfully(browser):
    driver = browser
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    # Login first
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    # Ensure logged in
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    # Perform logout
    wait.until(EC.element_to_be_clickable((By.ID, "logout-button"))).click()
    # Verify redirected to login page
    wait.until(EC.presence_of_element_located((By.ID, "login-button")))
    assert driver.current_url == BASE_URL
