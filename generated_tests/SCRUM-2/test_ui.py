import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
    if chromedriver_path:
        service = ChromeService(executable_path=chromedriver_path)
    else:
        service = ChromeService()
    driver = webdriver.Chrome(service=service, options=options)
    yield driver
    driver.quit()

BASE_URL = "http://127.0.0.1:8001/"
USERNAME = "testuser"
PASSWORD = "Password123"
INVALID_USERNAME = "invalid_user"
INVALID_PASSWORD = "WrongPassword123"

def login(driver, username, password):
    driver.get(BASE_URL)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).clear()
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "login-button").click()

def test_tc_001_login_with_valid_credentials(driver):
    login(driver, USERNAME, PASSWORD)
    wait = WebDriverWait(driver, 10)
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.text == "Dashboard"
    dashboard_message = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_message.text == "Welcome to the QA Demo Application"
    login_status_elements = driver.find_elements(By.ID, "login-status")
    if login_status_elements:
        assert not login_status_elements[0].is_displayed()

def test_tc_002_login_with_invalid_credentials(driver):
    login(driver, INVALID_USERNAME, INVALID_PASSWORD)
    wait = WebDriverWait(driver, 10)
    error_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert error_elem.text == "Invalid username or password"
    dashboard_titles = driver.find_elements(By.ID, "dashboard-title")
    assert len(dashboard_titles) == 0 or not dashboard_titles[0].is_displayed()

def test_tc_003_logout_successfully(driver):
    login(driver, USERNAME, PASSWORD)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    logout_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Logout']")))
    logout_button.click()
    wait.until(EC.url_to_be(BASE_URL))
    wait.until(EC.visibility_of_element_located((By.ID, "username")))
    dashboard_titles = driver.find_elements(By.ID, "dashboard-title")
    assert len(dashboard_titles) == 0 or not dashboard_titles[0].is_displayed()
