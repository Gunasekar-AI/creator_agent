import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    # TODO: Initialize WebDriver (e.g., Chrome) with appropriate options
    driver = webdriver.Chrome()
    driver.maximize_window()
    yield driver
    driver.quit()

def test_tc_001_login_valid_credentials(driver):
    # TODO: Set the login page URL
    driver.get("TODO_LOGIN_URL")
    wait = WebDriverWait(driver, 10)

    # TODO: Locate username field
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "TODO_USERNAME_FIELD_ID")))
    username_field.send_keys("TODO_VALID_USERNAME")

    # TODO: Locate password field
    password_field = driver.find_element(By.ID, "TODO_PASSWORD_FIELD_ID")
    password_field.send_keys("TODO_VALID_PASSWORD")

    # TODO: Locate and click login button
    login_button = driver.find_element(By.ID, "TODO_LOGIN_BUTTON_ID")
    login_button.click()

    # TODO: Verify navigation to home page, e.g., by checking a home page element
    wait.until(EC.visibility_of_element_located((By.ID, "TODO_HOME_PAGE_ELEMENT_ID")))

def test_tc_002_login_invalid_credentials(driver):
    driver.get("TODO_LOGIN_URL")
    wait = WebDriverWait(driver, 10)

    username_field = wait.until(EC.visibility_of_element_located((By.ID, "TODO_USERNAME_FIELD_ID")))
    username_field.send_keys("TODO_INVALID_USERNAME")

    password_field = driver.find_element(By.ID, "TODO_PASSWORD_FIELD_ID")
    password_field.send_keys("TODO_INVALID_PASSWORD")

    login_button = driver.find_element(By.ID, "TODO_LOGIN_BUTTON_ID")
    login_button.click()

    # TODO: Verify error message is displayed
    wait.until(EC.visibility_of_element_located((By.ID, "TODO_ERROR_MESSAGE_ELEMENT_ID")))

def test_tc_003_logout_successfully(driver):
    # Precondition: user is logged in
    # TODO: Perform login steps or assume session is already established
    # For simplicity, navigate to home page directly
    driver.get("TODO_HOME_PAGE_URL")
    wait = WebDriverWait(driver, 10)

    # TODO: Locate and click logout button
    logout_button = wait.until(EC.element_to_be_clickable((By.ID, "TODO_LOGOUT_BUTTON_ID")))
    logout_button.click()

    # Verify redirected to login page
    wait.until(EC.visibility_of_element_located((By.ID, "TODO_LOGIN_PAGE_ELEMENT_ID")))