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
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    dashboard_title = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "dashboard-title")))
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_title.is_displayed()
    assert dashboard_message.is_displayed()
    assert dashboard_title.text == "Dashboard"
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    dashboard_title = driver.find_element(By.ID, "dashboard-title")
    assert not dashboard_title.is_displayed()

def test_logout_skip():
    pytest.skip("Logout not implemented in the application")
