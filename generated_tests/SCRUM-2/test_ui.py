import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope='function')
def driver():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(0)
    yield driver
    driver.quit()

TIMEOUT = 10

def test_login_valid(driver):
    driver.get('http://127.0.0.1:8001/')
    wait = WebDriverWait(driver, TIMEOUT)
    username_elem = wait.until(EC.presence_of_element_located((By.ID, 'username')) )
    password_elem = wait.until(EC.presence_of_element_located((By.ID, 'password')) )
    login_btn = wait.until(EC.element_to_be_clickable((By.ID, 'login-button')) )
    username_elem.clear()
    username_elem.send_keys('testuser')
    password_elem.clear()
    password_elem.send_keys('Password123')
    login_btn.click()
    # Verify success message
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, 'login-status')) )
    assert status_elem.text == 'Login successful'
    # Verify dashboard title and message
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-title')) )
    assert dashboard_title.text == 'Dashboard'
    dashboard_message = wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-message')) )
    assert dashboard_message.text == 'Welcome to the QA Demo Application'

def test_login_invalid(driver):
    driver.get('http://127.0.0.1:8001/')
    wait = WebDriverWait(driver, TIMEOUT)
    username_elem = wait.until(EC.presence_of_element_located((By.ID, 'username')) )
    password_elem = wait.until(EC.presence_of_element_located((By.ID, 'password')) )
    login_btn = wait.until(EC.element_to_be_clickable((By.ID, 'login-button')) )
    username_elem.clear()
    username_elem.send_keys('invalid_user')
    password_elem.clear()
    password_elem.send_keys('WrongPassword123')
    login_btn.click()
    # Verify error message
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, 'login-status')) )
    assert status_elem.text == 'Invalid username or password'
    # Verify dashboard is not displayed
    dashboard_title = driver.find_element(By.ID, 'dashboard-title')
    assert not dashboard_title.is_displayed()

def test_logout_skip():
    pytest.skip('Logout not implemented in the application')

