import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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

def login(driver, username, password):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "username"))
    ).clear()
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-button").click()

def test_login_valid(driver):
    login(driver, "testuser", "Password123")
    status = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )
    assert status.is_displayed()
    assert status.text == "Login successful"
    dashboard_title = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-title"))
    )
    dashboard_message = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-message"))
    )
    assert dashboard_title.is_displayed()
    assert dashboard_title.text == "Dashboard"
    assert dashboard_message.is_displayed()
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    login(driver, "invalid_user", "WrongPassword123")
    status = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )
    assert status.is_displayed()
    assert status.text == "Invalid username or password"
    dashboard_title = driver.find_element(By.ID, "dashboard-title")
    assert not dashboard_title.is_displayed()
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert not dashboard_message.is_displayed()

def test_logout_skipped():
    pytest.skip("Logout not implemented in the application")
