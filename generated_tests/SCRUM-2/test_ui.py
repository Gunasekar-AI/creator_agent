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
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status.text == "Login successful"
    title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title.is_displayed()
    assert title.text == "Dashboard"
    message = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message.is_displayed()
    assert message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status.text == "Invalid username or password"
    # Verify dashboard is not displayed
    dashboard_elements = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    dashboard_msg_elements = driver.find_elements(By.ID, "dashboard-message")
    if dashboard_msg_elements:
        assert not dashboard_msg_elements[0].is_displayed()

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
