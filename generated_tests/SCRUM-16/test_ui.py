import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    options.add_argument("--window-size=1920,1080")
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        driver = webdriver.Chrome(executable_path=driver_path, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    try:
        yield driver
    finally:
        driver.quit()

def test_tc_001_login_with_valid_credentials(browser):
    url = "http://127.0.0.1:8001/"
    browser.get(url)
    wait = WebDriverWait(browser, 10)
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    assert username is not None and password is not None, "Credentials not set in environment"
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    title_text = browser.find_element(By.ID, "dashboard-title").text
    assert title_text == "Dashboard"
    message_text = browser.find_element(By.ID, "dashboard-message").text
    assert message_text == "Welcome to the QA Demo Application"
    wait.until(EC.invisibility_of_element_located((By.ID, "username")))

def test_tc_002_login_with_invalid_credentials(browser):
    url = "http://127.0.0.1:8001/"
    browser.get(url)
    wait = WebDriverWait(browser, 10)
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys("invalid_user")
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys("WrongPassword123")
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))

def test_tc_003_logout_successfully(browser):
    url = "http://127.0.0.1:8001/"
    browser.get(url)
    wait = WebDriverWait(browser, 10)
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    assert username is not None and password is not None, "Credentials not set in environment"
    wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
    wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, "login-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    wait.until(EC.element_to_be_clickable((By.ID, "logout-button"))).click()
    wait.until(EC.visibility_of_element_located((By.ID, "username")))
    wait.until(EC.invisibility_of_element_located((By.ID, "dashboard-section")))
