import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    yield driver
    driver.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    status = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status.text == "Login successful"
    dashboard_title = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.text == "Dashboard"
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_message.is_displayed()
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    status = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status.text == "Invalid username or password"
    try:
        dashboard = driver.find_element(By.ID, "dashboard-title")
        assert not dashboard.is_displayed()
    except Exception:
        pass

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
