import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="session")
def driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_valid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_field = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username_field.send_keys("testuser")
    password_field.send_keys("Password123")
    login_button.click()
    success_msg = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert success_msg.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_title.is_displayed()
    assert dashboard_title.text == "Dashboard"
    assert dashboard_message.is_displayed()
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_field = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username_field.send_keys("invalid_user")
    password_field.send_keys("WrongPassword123")
    login_button.click()
    error_msg = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert error_msg.text == "Invalid username or password"
    dashboard_titles = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_titles:
        assert not dashboard_titles[0].is_displayed()
    dashboard_messages = driver.find_elements(By.ID, "dashboard-message")
    if dashboard_messages:
        assert not dashboard_messages[0].is_displayed()

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
