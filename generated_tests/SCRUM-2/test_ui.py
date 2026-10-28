import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def browser():
    options = Options()
    if os.getenv("CHROME_BIN"):
        options.binary_location = os.getenv("CHROME_BIN")
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        driver = webdriver.Chrome(executable_path=driver_path, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    try:
        yield driver
    finally:
        driver.quit()

def test_tc_001_login_with_valid_credentials(browser):
    base_url = "http://127.0.0.1:8001/"
    browser.get(base_url)
    wait = WebDriverWait(browser, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    browser.find_element(By.ID, "password").send_keys("Password123")
    browser.find_element(By.ID, "login-button").click()
    title_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.text == "Dashboard"
    message_elem = browser.find_element(By.ID, "dashboard-message")
    assert message_elem.text == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(browser):
    base_url = "http://127.0.0.1:8001/"
    browser.get(base_url)
    wait = WebDriverWait(browser, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    browser.find_element(By.ID, "password").send_keys("WrongPassword123")
    browser.find_element(By.ID, "login-button").click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))

def test_tc_003_logout_successfully(browser):
    base_url = "http://127.0.0.1:8001/"
    browser.get(base_url)
    wait = WebDriverWait(browser, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    browser.find_element(By.ID, "password").send_keys("Password123")
    browser.find_element(By.ID, "login-button").click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    browser.find_element(By.ID, "logout-button").click()
    wait.until(EC.visibility_of_element_located((By.ID, "username")))
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))
