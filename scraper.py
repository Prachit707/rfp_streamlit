"""
MERX Opportunities Scraper
Production-ready version with comprehensive error handling and debugging.

Requirements:
- Network access must be enabled
- Chrome/Chromium browser installed
- Python packages: selenium
"""

import time
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MERXScraper:
    """Scraper for Canadian MERX procurement opportunities."""
    
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
        
    def _setup_driver(self):
        """Set up Chrome WebDriver with optimal options."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
        
        # Essential options for reliability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Realistic user agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Additional options for stability
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--start-maximized")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            logger.info("✓ Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def _find_search_box(self) -> Optional[object]:
        """
        Find the search box using multiple strategies.
        
        Returns:
            WebElement if found, None otherwise
        """
        logger.info("Looking for search box...")
        
        # Give page time to load
        time.sleep(5)
        
        if self.debug:
            # Save page source for debugging
            with open("/tmp/merx_page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.debug("Page source saved to /tmp/merx_page_source.html")
        
        # Get all input elements
        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
        logger.info(f"Found {len(all_inputs)} input elements on page")
        
        if self.debug:
            for i, inp in enumerate(all_inputs[:10]):
                logger.debug(
                    f"  Input {i}: type={inp.get_attribute('type')}, "
                    f"id={inp.get_attribute('id')}, "
                    f"class={inp.get_attribute('class')}, "
                    f"placeholder={inp.get_attribute('placeholder')}, "
                    f"visible={inp.is_displayed()}"
                )
        
        # Strategy 1: Search input type
        search_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='search']")
        for inp in search_inputs:
            if inp.is_displayed():
                logger.info("✓ Found search box (type='search')")
                return inp
        
        # Strategy 2: Placeholder contains "search"
        for inp in all_inputs:
            placeholder = (inp.get_attribute('placeholder') or "").lower()
            if 'search' in placeholder and inp.is_displayed():
                logger.info(f"✓ Found search box (placeholder='{placeholder}')")
                return inp
        
        # Strategy 3: Class contains "search"
        for inp in all_inputs:
            class_name = (inp.get_attribute('class') or "").lower()
            if 'search' in class_name and inp.is_displayed():
                logger.info(f"✓ Found search box (class='{class_name}')")
                return inp
        
        # Strategy 4: ID contains "search"
        for inp in all_inputs:
            input_id = (inp.get_attribute('id') or "").lower()
            if 'search' in input_id and inp.is_displayed():
                logger.info(f"✓ Found search box (id='{input_id}')")
                return inp
        
        # Strategy 5: Any visible text input (last resort)
        text_inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        for inp in text_inputs:
            if inp.is_displayed():
                logger.info("✓ Found text input (fallback)")
                return inp
        
        logger.error("✗ Could not find search box with any strategy")
        if self.debug:
            self.driver.save_screenshot("/tmp/merx_no_search_box.png")
            logger.debug("Screenshot saved to /tmp/merx_no_search_box.png")
        
        return None
    
    def _perform_search(self, search_term: str) -> bool:
        """
        Perform a search on MERX.
        
        Args:
            search_term: The term to search for
            
        Returns:
            True if search was successful, False otherwise
        """
        search_box = self._find_search_box()
        
        if not search_box:
            logger.error("Cannot perform search - no search box found")
            return False
        
        try:
            logger.info(f"Entering search term: '{search_term}'")
            search_box.click()
            time.sleep(0.5)
            search_box.clear()
            search_box.send_keys(search_term)
            time.sleep(0.5)
            search_box.send_keys(Keys.ENTER)
            
            # Wait for results
            logger.info("Waiting for search results...")
            time.sleep(5)
            
            if self.debug:
                self.driver.save_screenshot("/tmp/merx_after_search.png")
                logger.debug("Screenshot saved to /tmp/merx_after_search.png")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return False
    
    def _scrape_page(self, page_num: int) -> List[Dict]:
        """
        Scrape opportunities from the current page.
        
        Args:
            page_num: Current page number
            
        Returns:
            List of opportunity dictionaries
        """
        results = []
        
        # Try to find table rows
        rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        if not rows:
            logger.warning("No rows found with 'table tbody tr', trying alternative selectors")
            rows = self.driver.find_elements(By.CSS_SELECTOR, "tr")
        
        logger.info(f"Found {len(rows)} rows on page {page_num}")
        
        for idx, row in enumerate(rows):
            try:
                cols = row.find_elements(By.TAG_NAME, "td")
                
                if len(cols) < 4:
                    continue
                
                title = cols[0].text.strip()
                organization = cols[1].text.strip()
                closing_date = cols[3].text.strip()
                
                # Only add if we have actual data
                if title and organization:
                    result = {
                        "title": title,
                        "organization": organization,
                        "closing_date": closing_date,
                        "page": page_num,
                        "scraped_at": datetime.now().isoformat()
                    }
                    results.append(result)
                    
                    if self.debug:
                        logger.debug(f"  Row {idx}: {title[:50]}...")
                        
            except Exception as e:
                logger.debug(f"Error parsing row {idx}: {e}")
                continue
        
        logger.info(f"Collected {len(results)} opportunities from page {page_num}")
        return results
    
    def _go_to_next_page(self) -> bool:
        """
        Navigate to the next page of results.
        
        Returns:
            True if navigation was successful, False if no more pages
        """
        try:
            next_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[aria-label='Next page']"
            )
            
            if next_button.is_enabled():
                logger.info("Clicking next page button...")
                next_button.click()
                time.sleep(5)
                return True
            else:
                logger.info("Next button is disabled - no more pages")
                return False
                
        except NoSuchElementException:
            logger.info("No next button found - reached last page")
            return False
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def scrape(self, search_term: str = "health", max_pages: int = 3) -> List[Dict]:
        """
        Scrape MERX opportunities.
        
        Args:
            search_term: The term to search for
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of opportunity dictionaries
        """
        all_results = []
        
        try:
            # Set up driver
            self._setup_driver()
            
            # Navigate to MERX
            logger.info("Opening MERX opportunities page...")
            self.driver.get("https://www.merx.com/public/opportunities")
            
            # Perform search
            if not self._perform_search(search_term):
                logger.error("Search failed - aborting")
                return all_results
            
            # Scrape pages
            page = 1
            while page <= max_pages:
                logger.info(f"\n{'='*60}")
                logger.info(f"Scraping page {page}/{max_pages}")
                logger.info(f"{'='*60}")
                
                # Scrape current page
                page_results = self._scrape_page(page)
                all_results.extend(page_results)
                
                # Try to go to next page
                if page < max_pages:
                    if not self._go_to_next_page():
                        logger.info("No more pages available")
                        break
                
                page += 1
            
        except Exception as e:
            logger.error(f"Fatal error during scraping: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")
        
        return all_results
    
    def save_results(self, results: List[Dict], filename: str = "merx_results.json"):
        """
        Save results to a JSON file.
        
        Args:
            results: List of opportunity dictionaries
            filename: Output filename
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Results saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")


def main():
    """Main entry point."""
    print("="*70)
    print("MERX Opportunities Scraper")
    print("="*70)
    print()
    
    # Initialize scraper
    scraper = MERXScraper(
        headless=True,  # Set to False to see the browser
        debug=True      # Enable debug mode
    )
    
    # Run scraper
    results = scraper.scrape(
        search_term="health",
        max_pages=3
    )
    
    # Display results
    print("\n" + "="*70)
    print(f"SCRAPING COMPLETE - Found {len(results)} opportunities")
    print("="*70 + "\n")
    
    for i, opp in enumerate(results, 1):
        print(f"{i}. {opp['title']}")
        print(f"   Organization: {opp['organization']}")
        print(f"   Closes: {opp['closing_date']}")
        print(f"   Page: {opp['page']}")
        print()
    
    # Save results
    if results:
        scraper.save_results(results, "/tmp/merx_results.json")
        print(f"\n✓ Full results saved to /tmp/merx_results.json")
    else:
        print("\n⚠ No results to save")
    
    return results


if __name__ == "__main__":
    main()
