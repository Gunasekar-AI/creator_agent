import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    # TODO: configure WebDriver as needed (e.g., ChromeOptions)
    driver = webdriver.Chrome()
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_with_valid_credentials(driver):
    # TODO: set the login page URL
    login_url = "TODO_LOGIN_PAGE_URL"
    driver.get(login_url)

    wait = WebDriverWait(driver, 10)

    # TODO: locate username and password fields
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "TODO_USERNAME_FIELD_ID")))
    password_field = wait.until(EC.visibility_of_element_located((By.ID, "TODO_PASSWORD_FIELD_ID")))
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "TODO_LOGIN_BUTTON_ID")))

    # TODO: provide valid credentials
    username_field.send_keys("TODO_VALID_USERNAME")
    password_field.send_keys("TODO_VALID_PASSWORD")
    login_button.click()

    # TODO: verify navigation to home page (e.g., URL or unique element)
    home_indicator = wait.until(EC.visibility_of_element_located((By.ID, "TODO_HOME_PAGE_INDICATOR_ID")))
    assert home_indicator.is_displayed()

def test_login_with_invalid_credentials(driver):
    # TODO: set the login page URL
    login_url = "TODO_LOGIN_PAGE_URL"
    driver.get(login_url)

    wait = WebDriverWait(driver, 10)

    # TODO: locate username and password fields
    username_field = wait.until(EC.visibility_of_element_located((By.ID, "TODO_USERNAME_FIELD_ID")))
    password_field = wait.until(EC.visibility_of_element_located((By.ID, "TODO_PASSWORD_FIELD_ID")))
    login_button = wait.until(EC.element_to_be_clickable((By.ID, "TODO_LOGIN_BUTTON_ID")))

    # TODO: provide invalid credentials
    username_field.send_keys("TODO_INVALID_USERNAME")
    password_field.send_keys("TODO_INVALID_PASSWORD")
    login_button.click()

    # TODO: verify error message text
    error_msg = wait.until(EC.visibility_of_element_located((By.ID, "TODO_ERROR_MESSAGE_ID")))
    assert error_msg.text == "TODO_EXACT_ERROR_MESSAGE_TEXT"

def test_logout_successfully(driver):
    # Precondition: user is logged in.
    # TODO: implement login steps or reuse a helper.
    # For brevity, assume the user is already logged in.

    wait = WebDriverWait(driver, 10)

    # TODO: locate logout button
    logout_button = wait.until(EC.element_to_be_clickable((By.ID, "TODO_LOGOUT_BUTTON_ID")))
    logout_button.click()

    # TODO: verify redirection to login page
    login_page_indicator = wait.until(EC.visibility_of_element_located((By.ID, "TODO_LOGIN_PAGE_INDICATOR_ID")))
    assert login_page_indicator.is_displayed()
