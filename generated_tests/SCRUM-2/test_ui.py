import pytest
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.binary_location = os.environ.get("CHROME_BIN")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(os.environ["CHROMEDRIVER_PATH"])
    browser = webdriver.Chrome(service=service, options=options)

    try:
        yield browser
    finally:
        browser.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    driver.find_element(By.ID, "username").send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(driver, 10)
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    title_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.text == "Dashboard"
    message_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message_elem.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    driver.find_element(By.ID, "username").send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(driver, 10)
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    dashboard_elements = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    else:
        assert True

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
