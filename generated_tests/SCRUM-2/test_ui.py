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
    wait = WebDriverWait(driver, 10)
    username_elem = wait.until(EC.presence_of_element_located((By.ID, "username")))
    password_elem = driver.find_element(By.ID, "password")
    login_button = driver.find_element(By.ID, "login-button")
    username_elem.send_keys("testuser")
    password_elem.send_keys("Password123")
    login_button.click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "login-status"), "Login successful"))
    dashboard_title = wait.until(EC.presence_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.is_displayed()
    assert dashboard_title.text == "Dashboard"
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_message.is_displayed()
    assert dashboard_message.text == "Welcome to the QA Demo Application"

def test_login_invalid(driver):
    driver.get("http://127.0.0.1:8001/")
    wait = WebDriverWait(driver, 10)
    driver.find_element(By.ID, "username").send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    wait.until(EC.text_to_be_present_in_element((By.ID, "login-status"), "Invalid username or password"))
    try:
        dashboard_title = driver.find_element(By.ID, "dashboard-title")
        assert not dashboard_title.is_displayed()
    except NoSuchElementException:
        pass

@pytest.mark.skip(reason="Logout not implemented in the application")
def test_logout():
    pass
