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

def test_tc_001_login_with_valid_credentials(browser):
    base_url = os.getenv("BASE_URL")
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    wait = WebDriverWait(browser, 10)
    browser.get(base_url)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    title = browser.find_element(By.ID, "dashboard-title").text
    message = browser.find_element(By.ID, "dashboard-message").text
    assert title == "Dashboard"
    assert message == "Welcome to the QA Demo Application"
    status = browser.find_element(By.ID, "login-status").text
    assert "Login successful" in status

def test_tc_002_login_with_invalid_credentials(browser):
    base_url = os.getenv("BASE_URL")
    wait = WebDriverWait(browser, 10)
    browser.get(base_url)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys("invalid_pass")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    error = wait.until(EC.visibility_of_element_located((By.ID, "login-status"))).text
    assert "Invalid username or password" in error

def test_tc_003_logout_successfully(browser):
    base_url = os.getenv("BASE_URL")
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    wait = WebDriverWait(browser, 10)
    browser.get(base_url)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    wait.until(EC.element_to_be_clickable((By.ID, "logout-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "login-button")))
    assert browser.current_url == base_url
