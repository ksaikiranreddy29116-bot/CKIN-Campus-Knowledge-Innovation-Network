
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CKIN_URL = "https://ckin-campus-knowledge-innovation-network.onrender.com"

DEMO_EMAIL = "student@ckin.local"
DEMO_PASSWORD = "password123"


@pytest.fixture
def driver():
    browser = webdriver.Chrome()
    browser.set_window_size(1366, 900)
    browser.implicitly_wait(2)
    yield browser
    browser.quit()


def wait_for_page(driver):
    WebDriverWait(driver, 60).until(
        lambda browser: browser.execute_script(
            "return document.readyState"
        ) == "complete"
    )


def login_as_student(driver):
    driver.get(f"{CKIN_URL}/login")
    wait_for_page(driver)

    driver.find_element(By.NAME, "email").send_keys(DEMO_EMAIL)
    driver.find_element(By.NAME, "password").send_keys(DEMO_PASSWORD)
    driver.find_element(
        By.CSS_SELECTOR, "form button[type='submit']"
    ).click()

    WebDriverWait(driver, 30).until(
        lambda browser: "/login" not in browser.current_url
    )


# FT-01: Homepage loads and redirects to login when logged out
def test_homepage_loads(driver):
    driver.get(CKIN_URL)
    wait_for_page(driver)

    assert driver.current_url.startswith("https://")
    assert driver.title.strip() != ""
    assert len(driver.find_elements(By.TAG_NAME, "body")) == 1
    assert "/login" in driver.current_url


# FT-02: Invalid login must be rejected
def test_invalid_login_rejected(driver):
    driver.get(f"{CKIN_URL}/login")
    wait_for_page(driver)

    driver.find_element(By.NAME, "email").send_keys(
        "invalid-user@example.com"
    )
    driver.find_element(By.NAME, "password").send_keys(
        "WrongPassword123!"
    )
    driver.find_element(
        By.CSS_SELECTOR, "form button[type='submit']"
    ).click()

    WebDriverWait(driver, 15).until(
        lambda browser: "/login" in browser.current_url
    )

    assert driver.find_element(By.NAME, "password").is_displayed()


# FT-03: Project listing must require authentication
def test_projects_require_login(driver):
    driver.get(f"{CKIN_URL}/projects")
    wait_for_page(driver)

    WebDriverWait(driver, 15).until(
        lambda browser: "/login" in browser.current_url
    )

    assert "/login" in driver.current_url


# FT-04: Student can access the project creation page
def test_student_can_open_create_project(driver):
    login_as_student(driver)

    driver.get(f"{CKIN_URL}/projects/create")
    wait_for_page(driver)

    assert "/projects/create" in driver.current_url
    assert driver.find_element(By.NAME, "title").is_displayed()
    assert driver.find_element(By.NAME, "description").is_displayed()
    assert driver.find_element(By.NAME, "required_skills").is_displayed()



# FT-05: Server rejects project creation when required fields are missing
def test_project_creation_rejects_missing_fields(driver):
    login_as_student(driver)

    driver.get(f"{CKIN_URL}/projects/create")
    wait_for_page(driver)

    # Remove browser-side validation to test server-side validation.
    driver.execute_script("""
        document.querySelectorAll("form [required]").forEach(
            element => element.removeAttribute("required")
        );
    """)

    # Submit the form without clicking the obstructed button.
    driver.execute_script("""
        document.querySelector("form").submit();
    """)

    WebDriverWait(driver, 20).until(
        lambda browser: (
            "Please fill in all required fields."
            in browser.find_element(By.TAG_NAME, "body").text
        )
    )

    assert "/projects/create" in driver.current_url
    assert driver.find_element(By.NAME, "title").is_displayed()
