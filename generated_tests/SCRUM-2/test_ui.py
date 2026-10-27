import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_field = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username_field.send_keys("testuser")
    password_field.send_keys("Password123")
    login_button.click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    dashboard_message = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert dashboard_title.is_displayed()
    assert dashboard_message.is_displayed()
    assert dashboard_title.text == "Dashboard"
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_field = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username_field.send_keys("invalid_user")
    password_field.send_keys("WrongPassword123")
    login_button.click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    dashboard_title = driver.find_element(By.ID, "dashboard-title")
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert not dashboard_title.is_displayed()
    assert not dashboard_message.is_displayed()

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
