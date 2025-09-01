from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import os


class WebDriverManager:
    """Manages WebDriver setup and configuration"""
    
    def __init__(self):
        self.driver = None

    def setup_driver(self) -> webdriver.Edge:
        """Setup Edge WebDriver with EdgeChromiumDriverManager and fallback"""
        options = self._get_edge_options()
        
        try:
            service = Service(EdgeChromiumDriverManager().install())
            self.driver = webdriver.Edge(service=service, options=options)
        except Exception as e:
            edge_driver_path = os.getenv('EDGE_DRIVER_PATH')
            if not edge_driver_path:
                raise Exception("EDGE_DRIVER_PATH environment variable not set and EdgeChromiumDriverManager failed")
            print(f"Using edge driver path: {edge_driver_path}")
            service = Service(edge_driver_path)
            self.driver = webdriver.Edge(service=service, options=options)
        
        return self.driver

    def _get_edge_options(self) -> Options:
        """Configure Edge browser options for optimal scraping performance"""
        options = Options()
        
        # Basic options for stability
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0")
        options.page_load_strategy = 'normal'
        
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2, "plugins": 2, "popups": 2,
                "geolocation": 2, "notifications": 2, "media_stream": 2,
            }
        }
        options.add_experimental_option("prefs", prefs)
        
        return options

    def safe_find_element(self, by, value, timeout=10):
        """Safely find element with timeout"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def safe_find_elements(self, by, value, timeout=10):
        """Safely find multiple elements with timeout"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            return []

    def safe_click_element(self, element):
        """Safely click element using JavaScript if normal click fails"""
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)

    def wait_for_element_clickable(self, by, value, timeout=10):
        """Wait for element to be clickable and return it"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            return None

    def wait_for_text_in_element(self, by, value, text, timeout=10):
        """Wait for specific text to appear in element"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.text_to_be_present_in_element((by, value), text)
            )
        except TimeoutException:
            return False

    def scroll_to_element(self, element):
        """Scroll element into view"""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
        except Exception as e:
            print(f"Error scrolling to element: {e}")

    def get_element_text_safe(self, element):
        """Safely get text from element"""
        try:
            return element.text.strip()
        except Exception:
            return ""

    def get_element_attribute_safe(self, element, attribute):
        """Safely get attribute from element"""
        try:
            return element.get_attribute(attribute)
        except Exception:
            return ""

    def quit(self):
        """Safely quit the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None