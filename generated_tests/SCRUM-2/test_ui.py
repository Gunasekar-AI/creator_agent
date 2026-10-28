import os

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")

    # Required when running Chrome in a Linux CI container.
    if os.getenv("CHROME_BIN"):
        options.binary_location = os.environ["CHROME_BIN"]

    driver_path = os.getenv("CHROMEDRIVER_PATH")

    if driver_path:
        service = Service(executable_path=driver_path)
        browser = webdriver.Chrome(
            service=service,
            options=options,
        )
    else:
        browser = webdriver.Chrome(options=options)

    try:
        yield browser
    finally:
        browser.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    username_field.clear()
    username_field.send_keys("testuser")
    password_field.clear()
    password_field.send_keys("Password123")
    login_button.click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.text == "Dashboard"
    assert dashboard_title.is_displayed()
    dashboard_message = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert dashboard_message.text == "Welcome to the QA Demo Application"
    assert dashboard_message.is_displayed()

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    username_field.clear()
    username_field.send_keys("invalid_user")
    password_field.clear()
    password_field.send_keys("WrongPassword123")
    login_button.click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    try:
        dashboard = driver.find_element(By.ID, "dashboard-title")
        assert not dashboard.is_displayed()
    except NoSuchElementException:
        pass

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
