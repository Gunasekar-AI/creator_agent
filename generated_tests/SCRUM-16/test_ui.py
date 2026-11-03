import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture(scope="function")
def browser():
    options = Options()
    chrome_bin = os.getenv("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin
    driver_path = os.getenv("CHROMEDRIVER_PATH")
    if driver_path:
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    try:
        yield driver
    finally:
        driver.quit()

def test_tc_001_successful_login(browser):
    base_url = os.getenv("BASE_URL")
    username = os.getenv("TEST_USERNAME")
    password = os.getenv("TEST_PASSWORD")
    assert base_url, "BASE_URL environment variable not set"
    assert username, "TEST_USERNAME environment variable not set"
    assert password, "TEST_PASSWORD environment variable not set"
    browser.get(base_url)
    wait = WebDriverWait(browser, 10)
    user_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
    pass_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
    user_field.clear()
    user_field.send_keys(username)
    pass_field.clear()
    pass_field.send_keys(password)
    login_btn = wait.until(EC.element_to_be_clickable((By.ID, "login-button")))
    login_btn.click()
    dashboard_section = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-section")))
    assert dashboard_section.is_displayed()
    title_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-title")))
    assert title_elem.text == "Dashboard"
    message_elem = wait.until(EC.visibility_of_element_located((By.ID, "dashboard-message")))
    assert message_elem.text == "Welcome to the QA Demo Application"
    wait.until(EC.invisibility_of_element_located((By.ID, "username")))
    wait.until(EC.invisibility_of_element_located((By.ID, "password")))
    wait.until(EC.invisibility_of_element_located((By.ID, "login-button")))
