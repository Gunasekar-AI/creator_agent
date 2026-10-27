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

def test_login_valid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    title_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.is_displayed()
    assert title_elem.text == "Dashboard"
    message_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message_elem.is_displayed()
    assert message_elem.text == "Welcome to the QA Demo Application"

def test_login_invalid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    dashboard_elements = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    else:
        assert True

def test_logout_not_implemented():
    pytest.skip("Logout not implemented in the application")
