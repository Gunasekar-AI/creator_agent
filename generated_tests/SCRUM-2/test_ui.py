import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    dashboard_title = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.is_displayed()
    assert dashboard_title.text == "Dashboard"
    dashboard_msg = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_msg.is_displayed()
    assert dashboard_msg.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    # Verify dashboard is not displayed
    try:
        dashboard = driver.find_element(By.ID, "dashboard-title")
        assert not dashboard.is_displayed()
    except NoSuchElementException:
        pass

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
