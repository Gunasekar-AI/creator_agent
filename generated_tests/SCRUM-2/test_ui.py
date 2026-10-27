import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_valid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password = driver.find_element(By.ID, "password")
    login_btn = driver.find_element(By.ID, "login-button")
    username.send_keys("testuser")
    password.send_keys("Password123")
    login_btn.click()
    status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.text == "Dashboard"
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_message.text == "Welcome to the QA Demo Application"
    assert dashboard_title.is_displayed()
    assert dashboard_message.is_displayed()

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    username = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    password = driver.find_element(By.ID, "password")
    login_btn = driver.find_element(By.ID, "login-button")
    username.send_keys("invalid_user")
    password.send_keys("WrongPassword123")
    login_btn.click()
    status = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status.text == "Invalid username or password"
    dashboard_elements = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    else:
        assert True

@pytest.mark.skip(reason="Logout not implemented in the application")
def test_logout_skip():
    pass
