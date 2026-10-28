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
    options.add_argument("--window-size=1920,1080")
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        driver = webdriver.Chrome(executable_path=driver_path, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        driver.quit()

def test_tc_001_login_with_valid_credentials(browser):
    driver = browser
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys("Password123")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    title_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.text == "Dashboard"
    message_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message_elem.text == "Welcome to the QA Demo Application"

def test_tc_002_login_with_invalid_credentials(browser):
    driver = browser
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys("WrongPassword123")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    dashboard_section = driver.find_element(By.ID, "dashboard-section")
    assert not dashboard_section.is_displayed()

def test_tc_003_logout_successfully(browser):
    driver = browser
    wait = WebDriverWait(driver, 10)
    driver.get("http://127.0.0.1:8001/")
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys("Password123")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    wait.until(EC.element_to_be_clickable((By.ID, "logout-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "username")))
    dashboard_section = driver.find_element(By.ID, "dashboard-section")
    assert not dashboard_section.is_displayed()
