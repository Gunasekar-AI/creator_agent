import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def browser():
    options = webdriver.ChromeOptions()
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    options.add_argument("window-size=1920,1080")
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        from selenium.webdriver.chrome.service import Service
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        driver.quit()

def test_tc_001_login_with_valid_credentials(browser):
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing TEST_USERNAME or TEST_PASSWORD environment variable")
    base_url = "http://127.0.0.1:8001/"
    browser.get(base_url)
    browser.find_element(By.ID, "username").send_keys(username)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(browser, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert browser.find_element(By.ID, "dashboard-title").text == "Dashboard"
    assert browser.find_element(By.ID, "dashboard-message").text == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(browser):
    base_url = "http://127.0.0.1:8001/"
    browser.get(base_url)
    browser.find_element(By.ID, "username").send_keys("invalid_user")
    browser.find_element(By.ID, "password").send_keys("WrongPassword123")
    browser.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(browser, 10)
    login_status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert login_status.text == "Invalid username or password"
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))

def test_tc_003_logout_successfully(browser):
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    if not username or not password:
        raise RuntimeError("Missing TEST_USERNAME or TEST_PASSWORD environment variable")
    base_url = "http://127.0.0.1:8001/"
    browser.get(base_url)
    browser.find_element(By.ID, "username").send_keys(username)
    browser.find_element(By.ID, "password").send_keys(password)
    browser.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(browser, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    browser.find_element(By.ID, "logout-button").click()
    wait.until(EC.visibility_of_element_located((By.ID, "username")))
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))
