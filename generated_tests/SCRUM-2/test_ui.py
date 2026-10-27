import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope='function')
def driver():
    driver = webdriver.Chrome()
    driver.maximize_window()
    yield driver
    input('Press Enter to close Chrome...')
    driver.quit()

def test_login_valid(driver):
    driver.get('http://127.0.0.1:8001/')
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, 'username')))
    password_field = driver.find_element(By.ID, 'password')
    login_button = driver.find_element(By.ID, 'login-button')
    username_field.send_keys('testuser')
    password_field.send_keys('Password123')
    login_button.click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, 'login-status')))
    assert status_elem.text == 'Login successful'
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-title')))
    dashboard_message = wait.until(EC.visibility_of_element_located((By.ID, 'dashboard-message')))
    assert dashboard_title.is_displayed()
    assert dashboard_message.is_displayed()
    assert dashboard_title.text == 'Dashboard'
    assert dashboard_message.text == 'Welcome to the QA Demo Application'

def test_login_invalid(driver):
    driver.get('http://127.0.0.1:8001/')
    wait = WebDriverWait(driver, 10)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, 'username')))
    password_field = driver.find_element(By.ID, 'password')
    login_button = driver.find_element(By.ID, 'login-button')
    username_field.send_keys('invalid_user')
    password_field.send_keys('WrongPassword123')
    login_button.click()
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, 'login-status')))
    assert status_elem.text == 'Invalid username or password'
    dashboard_elements = driver.find_elements(By.ID, 'dashboard-title')
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    dashboard_msg_elements = driver.find_elements(By.ID, 'dashboard-message')
    if dashboard_msg_elements:
        assert not dashboard_msg_elements[0].is_displayed()

def test_logout_skip():
    pytest.skip('Logout not implemented in the application')
