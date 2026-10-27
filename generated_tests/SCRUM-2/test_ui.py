import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_valid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    ).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    # Verify login success message
    status_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )
    assert status_elem.text == "Login successful"
    # Verify dashboard title and message
    title_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-title"))
    )
    assert title_elem.text == "Dashboard"
    message_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "dashboard-message"))
    )
    assert message_elem.text == "Welcome to the QA Demo Application"

def test_login_invalid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    ).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    # Verify error message
    status_elem = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, "login-status"))
    )
    assert status_elem.text == "Invalid username or password"
    # Ensure dashboard is not displayed
    dashboard = driver.find_element(By.ID, "dashboard-title")
    assert not dashboard.is_displayed(), (
        "Dashboard should not be visible after invalid login"
    )
    with pytest.raises(TimeoutException):
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "dashboard-title"))
        )

def test_logout_not_implemented():
    pytest.skip("Logout not implemented in the application")
