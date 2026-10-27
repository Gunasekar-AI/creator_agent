import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

@pytest.fixture(scope="function")
def driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()

def test_login_with_valid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "username"))).send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    # verify success message
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    # verify dashboard title and message
    title_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.is_displayed()
    assert title_elem.text == "Dashboard"
    message_elem = driver.find_element(By.ID, "dashboard-message")
    assert message_elem.is_displayed()
    assert message_elem.text == "Welcome to the QA Demo Application"

def test_login_with_invalid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "username"))).send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    # verify error message
    status_elem = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    # verify dashboard not displayed
    try:
        dashboard_elem = driver.find_element(By.ID, "dashboard-title")
        assert not dashboard_elem.is_displayed()
    except NoSuchElementException:
        pass

def test_logout_not_implemented(driver):
    pytest.skip("Logout functionality is not implemented in the application.")
