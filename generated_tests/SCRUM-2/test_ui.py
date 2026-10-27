import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    # TODO: configure WebDriver (e.g., path to chromedriver)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_login_valid(driver):
    # TODO: set the login page URL
    driver.get("TODO_LOGIN_PAGE_URL")
    # Locate username and password fields
    username = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "TODO_USERNAME_FIELD_ID"))
    )
    password = driver.find_element(By.ID, "TODO_PASSWORD_FIELD_ID")
    # Enter valid credentials
    username.send_keys("TODO_VALID_USERNAME")
    password.send_keys("TODO_VALID_PASSWORD")
    # Click login button
    login_btn = driver.find_element(By.ID, "TODO_LOGIN_BUTTON_ID")
    login_btn.click()
    # Verify navigation to home page
    WebDriverWait(driver, 10).until(EC.url_contains("/home"))
    assert "/home" in driver.current_url

def test_login_invalid(driver):
    driver.get("TODO_LOGIN_PAGE_URL")
    username = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "TODO_USERNAME_FIELD_ID"))
    )
    password = driver.find_element(By.ID, "TODO_PASSWORD_FIELD_ID")
    username.send_keys("TODO_INVALID_USERNAME")
    password.send_keys("TODO_INVALID_PASSWORD")
    login_btn = driver.find_element(By.ID, "TODO_LOGIN_BUTTON_ID")
    login_btn.click()
    # Verify error message is displayed
    error_msg = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "TODO_ERROR_MESSAGE_ID"))
    )
    assert "TODO_ERROR_MESSAGE_TEXT" in error_msg.text

def test_logout_successful(driver):
    # Precondition: user is already logged in
    # TODO: implement login steps or navigate to a logged‑in state
    logout_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "TODO_LOGOUT_BUTTON_ID"))
    )
    logout_btn.click()
    # Verify redirection to login page
    WebDriverWait(driver, 10).until(EC.url_contains("TODO_LOGIN_PAGE_URL_AFTER_LOGOUT"))
    assert "TODO_LOGIN_PAGE_URL_AFTER_LOGOUT" in driver.current_url
