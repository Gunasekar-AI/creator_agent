import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def driver():
    # TODO: configure WebDriver (e.g., Chrome, options)
    driver = webdriver.Chrome()
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_with_valid_credentials(driver):
    # TODO: set login_page_url
    driver.get("TODO_LOGIN_PAGE_URL")
    # TODO: set selectors
    username_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_USERNAME_SELECTOR"))
    )
    password_field = driver.find_element(By.CSS_SELECTOR, "TODO_PASSWORD_SELECTOR")
    login_button = driver.find_element(By.CSS_SELECTOR, "TODO_LOGIN_BUTTON_SELECTOR")
    username_field.send_keys("TODO_VALID_USERNAME")
    password_field.send_keys("TODO_VALID_PASSWORD")
    login_button.click()
    # TODO: verify navigation to home page, e.g., by checking a home page element or URL
    home_indicator = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_HOME_INDICATOR_SELECTOR"))
    )
    assert home_indicator.is_displayed()

def test_login_with_invalid_credentials(driver):
    driver.get("TODO_LOGIN_PAGE_URL")
    username_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_USERNAME_SELECTOR"))
    )
    password_field = driver.find_element(By.CSS_SELECTOR, "TODO_PASSWORD_SELECTOR")
    login_button = driver.find_element(By.CSS_SELECTOR, "TODO_LOGIN_BUTTON_SELECTOR")
    username_field.send_keys("TODO_INVALID_USERNAME")
    password_field.send_keys("TODO_INVALID_PASSWORD")
    login_button.click()
    error_msg = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_ERROR_MESSAGE_SELECTOR"))
    )
    # TODO: replace with expected error text
    assert "TODO_ERROR_MESSAGE_TEXT" in error_msg.text

def test_logout_successfully(driver):
    # Assume user is already logged in; TODO: implement login steps or session setup
    # TODO: navigate to a page where logout button is visible
    logout_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "TODO_LOGOUT_BUTTON_SELECTOR"))
    )
    logout_button.click()
    # Verify redirect to login page
    WebDriverWait(driver, 10).until(EC.url_contains("TODO_LOGIN_PAGE_URL"))
    assert driver.current_url == "TODO_LOGIN_PAGE_URL"
