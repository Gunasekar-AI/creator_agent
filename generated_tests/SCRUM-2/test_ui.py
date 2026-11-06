import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

@pytest.fixture(scope="function")
def browser():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    yield driver
    try:
        driver.quit()
    finally:
        pass

BASE_URL = os.getenv("BASE_URL")
USERNAME = os.getenv("TEST_USERNAME")
PASSWORD = os.getenv("TEST_PASSWORD")

def test_tc_001_login_with_valid_credentials(browser):
    driver = browser
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title"))).text
    message = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message"))).text
    assert title == "Dashboard"
    assert message == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(browser):
    driver = browser
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys("invalid_pass")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    error = wait.until(EC.visibility_of_element_located((By.ID, "login-status"))).text
    assert error == "Invalid username or password"

def test_tc_003_logout_successfully(browser):
    driver = browser
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
    wait.until(EC.presence_of_element_located((By.ID, "password"))).send_keys(PASSWORD)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    wait.until(EC.element_to_be_clickable((By.ID, "logout-button"))).click()
    wait.until(EC.presence_of_element_located((By.ID, "username")))
    assert driver.current_url == BASE_URL
