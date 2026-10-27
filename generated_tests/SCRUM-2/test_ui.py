import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    yield driver
    input("Press Enter to close Chrome...")
    driver.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_elem = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_elem = driver.find_element(By.ID, "password")
    login_btn = driver.find_element(By.ID, "login-button")
    username_elem.send_keys("testuser")
    password_elem.send_keys("Password123")
    login_btn.click()
    login_status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert login_status.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    dashboard_message = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert dashboard_title.text == "Dashboard"
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username_elem = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password_elem = driver.find_element(By.ID, "password")
    login_btn = driver.find_element(By.ID, "login-button")
    username_elem.send_keys("invalid_user")
    password_elem.send_keys("WrongPassword123")
    login_btn.click()
    login_status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert login_status.text == "Invalid username or password"
    dashboard_elements = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    else:
        pass

def test_logout_skip():
    pytest.skip("Logout not implemented in the application.")
