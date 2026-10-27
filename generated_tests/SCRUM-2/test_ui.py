import os

import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

VALID_USER = "testuser"
VALID_PASS = "Password123"
INVALID_USER = "wronguser"
INVALID_PASS = "wrongpass"


@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    drv = webdriver.Chrome(options=options)
    drv.implicitly_wait(5)
    yield drv
    drv.quit()


def _login(driver, username, password):
    driver.get(BASE_URL + "/")
    wait = WebDriverWait(driver, 10)
    user_field = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    pass_field = driver.find_element(By.ID, "password")
    button = driver.find_element(By.ID, "login-button")
    user_field.send_keys(username)
    pass_field.send_keys(password)
    button.click()
    return wait


def test_login_with_valid_credentials(driver):
    wait = _login(driver, VALID_USER, VALID_PASS)

    dashboard_title = wait.until(
        EC.visibility_of_element_located((By.ID, "dashboard-title"))
    )
    assert dashboard_title.is_displayed()

    status = driver.find_element(By.ID, "login-status")
    wait.until(lambda d: status.text != "")
    assert status.text == "Login successful"


def test_login_with_invalid_credentials(driver):
    wait = _login(driver, INVALID_USER, INVALID_PASS)

    status = wait.until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )
    wait.until(lambda d: status.text != "")
    assert status.text == "Invalid username or password"

    assert not driver.find_element(By.ID, "dashboard-title").is_displayed()


@pytest.mark.xfail(
    reason="Demo app has no logout control or /logout route; "
           "scenario came from the Jira ticket, not the implementation.",
    strict=True,
)
def test_logout_successfully(driver):
    _login(driver, VALID_USER, VALID_PASS)
    driver.find_element(By.ID, "logout-button")