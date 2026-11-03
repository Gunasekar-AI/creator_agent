import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

@pytest.fixture
def browser():
    options = webdriver.ChromeOptions()
    chrome_bin = os.getenv('CHROME_BIN')
    if chrome_bin:
        options.binary_location = chrome_bin
    driver_path = os.getenv('CHROMEDRIVER_PATH')
    if driver_path:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    try:
        yield driver
    finally:
        driver.quit()

def test_tc_001_successful_login(browser):
    base_url = os.getenv('BASE_URL', 'http://127.0.0.1:8001')
    username = os.getenv('TEST_USERNAME')
    password = os.getenv('TEST_PASSWORD')
    if not username or not password:
        raise RuntimeError('Missing TEST_USERNAME or TEST_PASSWORD environment variables')
    driver = browser
    driver.get(base_url)

    wait = WebDriverWait(driver, 10)

    # Verify login form is displayed
    wait.until(EC.visibility_of_element_located((By.ID, 'username')))
    wait.until(EC.visibility_of_element_located((By.ID, 'password')))
    wait.until(EC.element_to_be_clickable((By.ID, 'login-button')))

    # Enter credentials
    driver.find_element(By.ID, 'username').send_keys(username)
    driver.find_element(By.ID, 'password').send_keys(password)

    # Click login
    driver.find_element(By.ID, 'login-button').click()

    # Wait for dashboard to be visible
    wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-section')))

    # Verify dashboard title
    title_elem = wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-title')))
    assert title_elem.text == 'Dashboard', f'Expected dashboard title "Dashboard", got "{title_elem.text}"'

    # Verify welcome message
    message_elem = wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-message')))
    assert 'Welcome to the QA Demo Application' in message_elem.text, \
        f'Expected welcome message to contain "Welcome to the QA Demo Application", got "{message_elem.text}"'

    # Verify login form is no longer visible
    wait.until(EC.invisibility_of_element_located((By.ID, 'username')))
