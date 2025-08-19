from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
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

    def safe_click_element(self, element):
        """Safely click element using JavaScript if normal click fails"""
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)

    def quit(self):
        """Safely quit the driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None