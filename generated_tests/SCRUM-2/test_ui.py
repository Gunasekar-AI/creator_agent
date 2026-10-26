import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_with_valid_credentials(driver):
    # TODO: Set the login page URL
    login_url = "TODO_LOGIN_URL"
    driver.get(login_url)

    # TODO: Locate username field
    username = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_USERNAME_SELECTOR"))
    )
    username.send_keys("TODO_VALID_USERNAME")

    # TODO: Locate password field
    password = driver.find_element(By.CSS_SELECTOR, "TODO_PASSWORD_SELECTOR")
    password.send_keys("TODO_VALID_PASSWORD")

    # TODO: Locate and click login button
    login_btn = driver.find_element(By.CSS_SELECTOR, "TODO_LOGIN_BUTTON_SELECTOR")
    login_btn.click()

    # TODO: Verify navigation to home page (e.g., presence of a home page element)
    home_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_HOME_INDICATOR_SELECTOR"))
    )
    assert home_elem.is_displayed()

def test_login_with_invalid_credentials(driver):
    # TODO: Set the login page URL
    login_url = "TODO_LOGIN_URL"
    driver.get(login_url)

    # TODO: Locate username field
    username = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_USERNAME_SELECTOR"))
    )
    username.send_keys("TODO_INVALID_USERNAME")

    # TODO: Locate password field
    password = driver.find_element(By.CSS_SELECTOR, "TODO_PASSWORD_SELECTOR")
    password.send_keys("TODO_INVALID_PASSWORD")

    # TODO: Locate and click login button
    login_btn = driver.find_element(By.CSS_SELECTOR, "TODO_LOGIN_BUTTON_SELECTOR")
    login_btn.click()

    # TODO: Verify error message is displayed
    error_msg = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "TODO_ERROR_MESSAGE_SELECTOR"))
    )
    # TODO: Replace with expected error text
    assert "TODO_ERROR_MESSAGE_TEXT" in error_msg.text

def test_logout_successful(driver):
    # TODO: Ensure the user is logged in before logout, e.g., navigate to a logged-in page
    driver.get("TODO_LOGGED_IN_URL")

    # TODO: Locate and click logout button
    logout_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "TODO_LOGOUT_BUTTON_SELECTOR"))
    )
    logout_btn.click()

    # TODO: Verify redirect to login page
    WebDriverWait(driver, 10).until(EC.url_contains("TODO_LOGIN_URL"))
    assert driver.current_url.startswith("TODO_LOGIN_URL")

