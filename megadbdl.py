from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener
import os
import logging
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NetworkListener(AbstractEventListener):
    def __init__(self):
        self.download_url = None

    def before_navigate_to(self, url, driver):
        if 'fs18.megadb.xyz' in url and '/d/' in url:
            self.download_url = url
            logger.info(f"Captured download URL: {url}")

def wait_for_download_url(driver, timeout=30):
    def check_for_download_url(driver):
        try:
            # Check network requests
            for request in driver.get_log('performance'):
                match = re.search(r'(http://fs18\.megadb\.xyz:8080/d/[^"]+)', str(request))
                if match:
                    return match.group(1)
            
            # Check page content
            page_source = driver.page_source
            match = re.search(r'(http://fs18\.megadb\.xyz:8080/d/[^"]+)', page_source)
            if match:
                return match.group(1)
            
            # Check iframe sources
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                src = iframe.get_attribute('src')
                if src and 'fs18.megadb.xyz' in src and '/d/' in src:
                    return src
                
            return False
        except Exception as e:
            logger.error(f"Error while checking for download URL: {str(e)}")
            return False

    try:
        return WebDriverWait(driver, timeout).until(check_for_download_url)
    except TimeoutException:
        return None

def retrieve_download_url(api_key: str, captcha_url: str) -> str:
    chrome_options = Options()
    chrome_options.add_extension("CaptchaSolver.crx")
    chrome_options.add_extension("adblock.crx")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    
    # Enable performance logging
    chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL', 'browser': 'ALL'})
    
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": "C:\\",
        "download.prompt_for_download": True,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    })

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Add network listener
    network_listener = NetworkListener()
    driver = EventFiringWebDriver(driver, network_listener)

    try:
        if not wait_for_extensions_to_load(driver):
            raise TimeoutException("Extensions did not load in time")

        logger.info("Extensions loaded successfully")

        # Close the Adblock extension tab (usually tab 3, index 2)
        driver.switch_to.window(driver.window_handles[2])
        driver.close()

        # Focus back on tab 2 (index 1)
        driver.switch_to.window(driver.window_handles[1])

        api_key_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "apiKey"))
        )
        api_key_input.send_keys(api_key)
        logger.info("API key entered")

        connect_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "connect"))
        )
        connect_button.click()
        logger.info("Connect button clicked")

        # Wait for and handle the alert
        alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
        alert.accept()
        logger.info("Alert accepted")

        # Toggle the checkbox
        auto_submit_checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "autoSubmitForms"))
        )
        if not auto_submit_checkbox.is_selected():
            auto_submit_checkbox.click()
        logger.info("Auto-submit checkbox toggled")

        # Navigate to the target URL
        driver.get(captcha_url)
        logger.info(f"Navigated to captcha URL: {captcha_url}")
        
        # Handle captcha solver
        captcha_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "captcha-solver.captcha-solver_inner"))
        )
        captcha_div.click()
        logger.info("Captcha solver clicked")
        driver.switch_to.window(driver.window_handles[2])
        driver.close()

        # Focus back on tab 2 (index 1)
        driver.switch_to.window(driver.window_handles[1])
        # Check for "ERROR_ZERO_BALANCE"
        try:
            error_div = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'ERROR_ZERO_BALANCE')]"))
            )
            if error_div:
                logger.error("Error: Zero balance detected!")
                return "ERROR_ZERO_BALANCE"
        except TimeoutException:
            pass

        # Wait for redirection
        WebDriverWait(driver, 90).until(EC.url_changes(driver.current_url))
        logger.info("Redirection successful!")

        

        # Check again for "ERROR_ZERO_BALANCE"
        try:
            error_div = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'ERROR_ZERO_BALANCE')]"))
            )
            if error_div:
                logger.error("Error: Zero balance detected after redirection!")
                return "ERROR_ZERO_BALANCE"
        except TimeoutException:
            pass

        # Check again for captcha solver success
        captcha_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "captcha-solver.captcha-solver_inner"))
        )
        captcha_div.click()
        logger.info("Captcha solver clicked again")

        WebDriverWait(driver, 120).until(
            EC.text_to_be_present_in_element_attribute(
                (By.CLASS_NAME, "captcha-solver.captcha-solver_inner"), "data-state", "solved"
            )
        )
        logger.info("Captcha solved successfully!")

        # Wait for the download URL
        download_url = wait_for_download_url(driver) or network_listener.download_url
        
        if not download_url:
            # Try switching to any new window/tab that might have opened
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                new_url = wait_for_download_url(driver)
                if new_url:
                    download_url = new_url
                    break

        if download_url:
            logger.info(f"Successfully captured download URL: {download_url}")
            return download_url
        else:
            logger.warning("No download URL found")
            return "Download URL capture failed!"

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        return str(e)
    finally:
        driver.quit()
        logger.info("WebDriver closed")

def wait_for_extensions_to_load(driver, timeout=10):
    def extensions_loaded(driver):
        return len(driver.window_handles) >= 3

    try:
        WebDriverWait(driver, timeout).until(extensions_loaded)
        return True
    except TimeoutException:
        return False

if __name__ == "__main__":
    api_key = ""
    captcha_url = "https://megadb.net/1b8savf8mhfs"

    download_url = retrieve_download_url(api_key, captcha_url)
    print(f"Final download URL: {download_url}")