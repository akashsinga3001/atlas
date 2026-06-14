# backend/app/services/selenium.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, TimeoutException

from app.utils.logger import get_logger

logger = get_logger(__name__)


class SeleniumService:
    """Service class to handle Selenium WebDriver interactions for automating web tasks."""

    def __init__(self):
        self.driver = self._setup_driver()
        self.wait = WebDriverWait(self.driver, 30)

    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Selenium WebDriver with necessary options."""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')

        driver = webdriver.Chrome(options=chrome_options)
        logger.info('Headless Chrome WebDriver initialized')
        return driver

    def find_first_present(self, locators: list[tuple[str, str]], element_name: str, timeout_seconds: int = 6):
        """Return the first present element from a list of locator candidates."""
        for locator in locators:
            try:
                return WebDriverWait(self.driver, timeout_seconds).until(EC.presence_of_element_located(locator))
            except TimeoutException:
                continue
        raise RuntimeError(f'Unable to locate {element_name} using provided locators.')

    def find_first_clickable(self, locators: list[tuple[str, str]], element_name: str, timeout_seconds: int = 6):
        """Return the first clickable element from a list of locator candidates."""
        for locator in locators:
            for _ in range(2):
                try:
                    return WebDriverWait(self.driver, timeout_seconds).until(EC.element_to_be_clickable(locator))
                except (TimeoutException, StaleElementReferenceException):
                    continue
        raise RuntimeError(f'Unable to locate clickable {element_name} using provided locators.')

    def safe_click(self, element) -> None:
        """Click element with JS fallback when regular click is blocked by transient DOM state."""
        try:
            element.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            self.driver.execute_script('arguments[0].click();', element)

    def fill_input(self, element, value: str) -> None:
        """Fill input element with value, clearing existing content first."""
        element.clear()
        element.send_keys(value)

    def close_driver(self):
        """Close the Selenium WebDriver."""
        if self.driver:
            self.driver.quit()
            logger.info('Selenium WebDriver closed successfully')
