
import os
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001").rstrip("/")
LOGIN_URL = f"{BASE_URL}/"

VALID_USERNAME = os.getenv("TEST_USERNAME", "testuser")
VALID_PASSWORD = os.getenv("TEST_PASSWORD", "Password123")


@pytest.fixture
def driver():
    browser = webdriver.Chrome()
    browser.set_window_size(1280, 900)
    yield browser
    browser.quit()


def login(driver, username, password):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, 10)

    wait.until(
        EC.visibility_of_element_located((By.ID, "username"))
    ).send_keys(username)

    driver.find_element(By.ID, "password").send_keys(password)

    wait.until(
        EC.element_to_be_clickable((By.ID, "login-button"))
    ).click()

    return wait.until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )


def test_login_with_valid_credentials(driver):
    status = login(driver, VALID_USERNAME, VALID_PASSWORD)
    assert status.text == "Login successful"

    title = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-title"))
    )
    assert title.text == "Dashboard"

    message = driver.find_element(By.ID, "dashboard-message")
    assert message.text == "Welcome to the QA Demo Application"


def test_login_with_invalid_credentials(driver):
    status = login(driver, "invalid_user", "WrongPassword123")
    assert status.text == "Invalid username or password"

    title = driver.find_element(By.ID, "dashboard-title")
    assert not title.is_displayed()


def test_logout_successfully():
    pytest.skip(
        "Logout cannot be tested yet: the demo app has no logout feature."
    )
