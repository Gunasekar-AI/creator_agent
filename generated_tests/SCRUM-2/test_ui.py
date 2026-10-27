import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_login_valid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username.send_keys("testuser")
    password.send_keys("Password123")
    login_button.click()
    login_status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert login_status.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.is_displayed()
    assert dashboard_title.text == "Dashboard"
    dashboard_message = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert dashboard_message.is_displayed()
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username.send_keys("invalid_user")
    password.send_keys("WrongPassword123")
    login_button.click()
    login_status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert login_status.text == "Invalid username or password"
    dashboard_title = driver.find_element(By.ID, "dashboard-title")
    assert not dashboard_title.is_displayed()

def test_logout_not_implemented():
    pytest.skip("Logout not implemented in the application")
