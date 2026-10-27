import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()

def test_login_with_valid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    driver.find_element(By.ID, "username").send_keys("testuser")
    driver.find_element(By.ID, "password").send_keys("Password123")
    driver.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(driver, 10)
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Login successful"
    dashboard_title = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert dashboard_title.is_displayed()
    assert dashboard_title.text == "Dashboard"
    dashboard_msg = driver.find_element(By.ID, "dashboard-message")
    assert dashboard_msg.is_displayed()
    assert dashboard_msg.text == "Welcome to the QA Demo Application"

def test_login_with_invalid_credentials(driver):
    driver.get("http://127.0.0.1:8001/")
    driver.find_element(By.ID, "username").send_keys("invalid_user")
    driver.find_element(By.ID, "password").send_keys("WrongPassword123")
    driver.find_element(By.ID, "login-button").click()
    wait = WebDriverWait(driver, 10)
    status_elem = wait.until(EC.visibility_of_element_located((By.ID, "login-status")))
    assert status_elem.text == "Invalid username or password"
    # Verify dashboard is not displayed
    dashboard_elements = driver.find_elements(By.ID, "dashboard-title")
    if dashboard_elements:
        assert not dashboard_elements[0].is_displayed()
    else:
        assert True

@pytest.mark.skip(reason="Logout not implemented in the application")
def test_logout_successful():
    pass
