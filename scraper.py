"""
MERX Scraper - Enhanced with Date Filter
Uses: https://www.merx.com/public/solicitations/open
"""

import time
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MERXScraper:
    """Scraper for Canadian MERX procurement solicitations."""
    
    def __init__(self, headless: bool = True, debug: bool = False):
        """
        Initialize the MERX scraper.
        
        Args:
            headless: Run Chrome in headless mode (no GUI)
            debug: Enable debug mode with screenshots and page source dumps
        """
        self.headless = headless
        self.debug = debug
        self.driver = None
        self.wait = None
        self.base_url = "https://www.merx.com/public/solicitations/open"
        
    def _setup_driver(self):
        """Set up Chrome WebDriver with optimal options."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("✓ Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def _find_search_box(self) -> Optional[object]:
        """Find the search box using multiple strategies."""
        logger.info("Looking for search box...")
        time.sleep(5)
        
        if self.debug:
            with open("/tmp/merx_page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.debug("Page source saved to /tmp/merx_page_source.html")
            self.driver.save_screenshot("/tmp/merx_initial_page.png")
        
        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
        logger.info(f"Found {len(all_inputs)} input elements on page")
        
        # Try multiple strategies
        search_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='search']")
        for inp in search_inputs:
            if inp.is_displayed():
                logger.info("✓ Found search box (type='search')")
                return inp
        
        for inp in all_inputs:
            placeholder = (inp.get_attribute('placeholder') or "").lower()
            if 'search' in placeholder and inp.is_displayed():
                logger.info(f"✓ Found search box (placeholder='{placeholder}')")
                return inp
        
        for inp in all_inputs:
            class_name = (inp.get_attribute('class') or "").lower()
            if 'search' in class_name and inp.is_displayed():
                logger.info(f"✓ Found search box (class='{class_name}')")
                return inp
        
        text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        for inp in text_inputs:
            if inp.is_displayed():
                logger.info("✓ Found text input (fallback)")
                return inp
        
        logger.warning("⚠ Could not find search box")
        return None
    
    def _perform_search(self, search_term: str) -> bool:
        """Perform a search on MERX."""
        search_box = self._find_search_box()
        
        if not search_box:
            logger.warning("No search box found - will scrape all visible solicitations")
            return True
        
        try:
            logger.info(f"Entering search term: '{search_term}'")
            search_box.click()
            time.sleep(0.5)
            search_box.clear()
            search_box.send_keys(search_term)
            time.sleep(0.5)
            search_box.send_keys(Keys.ENTER)
            logger.info("Waiting for search results...")
            time.sleep(5)
            
            if self.debug:
                self.driver.save_screenshot("/tmp/merx_after_search.png")
            
            return True
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return False
