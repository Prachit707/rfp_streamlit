"""
MERX Scraper - Enhanced Version
Extracts: Title, Organization, Published Date, Closing Date, and Link
"""

import time
import json
import logging
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
            self.driver.save_screenshot("/tmp/merx_initial_page.png")
        
        # Get all input elements
        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
        logger.info(f"Found {len(all_inputs)} input elements on page")
        
        if self.debug:
            for i, inp in enumerate(all_inputs[:15]):
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
        
        logger.warning("⚠ Could not find search box - page might not have one")
        if self.debug:
            self.driver.save_screenshot("/tmp/merx_no_search_box.png")
        
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
            logger.warning("No search box found - will scrape all visible solicitations")
            return True  # Continue anyway, just without search
        
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
            
            return True
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return False
    
    def _extract_link_from_row(self, row) -> Optional[str]:
        """
        Extract the opportunity link from a row.
        
        Args:
            row: WebElement representing a table row
            
        Returns:
            Full URL to the opportunity, or None if not found
        """
        try:
            # Try to find a link in the row
            links = row.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                href = link.get_attribute('href')
                if href and ('view-notice' in href or 'solicitation' in href):
                    return href
            
            # If no specific link found, return first link
            if links:
                return links[0].get_attribute('href')
                
        except Exception as e:
            logger.debug(f"Error extracting link: {e}")
        
        return None
    
    def _scrape_page(self, page_num: int) -> List[Dict]:
        """
        Scrape solicitations from the current page.
        
        Args:
            page_num: Current page number
            
        Returns:
            List of solicitation dictionaries
        """
        results = []
        
        # Try multiple selectors to find the data
        selectors_to_try = [
            "table tbody tr",
            "tr",
            "div[role='row']",
            ".solicitation-row",
            ".opportunity-row",
            "li.solicitation",
        ]
        
        rows = []
        for selector in selectors_to_try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if rows:
                logger.info(f"Found {len(rows)} rows using selector: {selector}")
                break
        
        if not rows:
            logger.warning("No rows found with any selector")
            return results
        
        for idx, row in enumerate(rows):
            try:
                # Try to extract text from the row
                row_text = row.text.strip()
                
                if not row_text:
                    continue
                
                # Extract link
                link = self._extract_link_from_row(row)
                
                # Try to find columns (td elements)
                cols = row.find_elements(By.TAG_NAME, "td")
                
                if cols and len(cols) >= 3:
                    # Structured table format
                    # Typical MERX structure:
                    # Col 0: Title
                    # Col 1: Organization
                    # Col 2: Published Date
                    # Col 3: Closing Date
                    
                    title = cols[0].text.strip() if len(cols) > 0 else ""
                    organization = cols[1].text.strip() if len(cols) > 1 else ""
                    
                    # Try to find both dates
                    if len(cols) >= 4:
                        published_date = cols[2].text.strip()
                        closing_date = cols[3].text.strip()
                    elif len(cols) == 3:
                        # If only 3 columns, assume no published date
                        published_date = ""
                        closing_date = cols[2].text.strip()
                    else:
                        published_date = ""
                        closing_date = cols[-1].text.strip()
                    
                else:
                    # Fallback: parse from row text
                    lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                    title = lines[0] if len(lines) > 0 else row_text[:100]
                    organization = lines[1] if len(lines) > 1 else ""
                    
                    # Try to find dates in the lines
                    published_date = ""
                    closing_date = ""
                    
                    for line in lines:
                        # Look for date patterns (YYYY-MM-DD or DD/MM/YYYY or similar)
                        if any(char.isdigit() for char in line):
                            if not published_date and len(line) < 30:
                                published_date = line
                            elif not closing_date and len(line) < 30:
                                closing_date = line
                
                # Only add if we have actual data
                if title and len(title) > 5:  # Ignore very short/empty titles
                    result = {
                        "title": title,
                        "organization": organization,
                        "published_date": published_date,
                        "closing_date": closing_date,
                        "link": link or "",
                        "page": page_num,
                        "scraped_at": datetime.now().isoformat()
                    }
                    results.append(result)
                    
                    if self.debug and idx < 5:  # Log first 5 for debugging
                        logger.debug(f"  Row {idx}:")
                        logger.debug(f"    Title: {title[:50]}...")
                        logger.debug(f"    Org: {organization[:40]}")
                        logger.debug(f"    Published: {published_date}")
                        logger.debug(f"    Closes: {closing_date}")
                        logger.debug(f"    Link: {link}")
                        
            except Exception as e:
                logger.debug(f"Error parsing row {idx}: {e}")
                continue
        
        logger.info(f"Collected {len(results)} solicitations from page {page_num}")
        return results
    
    def _go_to_next_page(self) -> bool:
        """
        Navigate to the next page of results.
        
        Returns:
            True if navigation was successful, False if no more pages
        """
        # Try multiple selectors for the next button
        next_button_selectors = [
            "button[aria-label='Next page']",
            "button[aria-label='next']",
            "a.next",
            "button.next",
            ".pagination-next",
            "li.next a",
        ]
        
        for selector in next_button_selectors:
            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                if next_button.is_enabled() and next_button.is_displayed():
                    logger.info(f"Clicking next page button (selector: {selector})...")
                    next_button.click()
                    time.sleep(5)
                    return True
                    
            except NoSuchElementException:
                continue
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        logger.info("No next button found - reached last page")
        return False
    
    def scrape(self, search_term: str = "health", max_pages: int = 3) -> List[Dict]:
        """
        Scrape MERX solicitations.
        
        Args:
            search_term: The term to search for
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of solicitation dictionaries
        """
        all_results = []
        
        try:
            # Set up driver
            self._setup_driver()
            
            # Navigate to MERX solicitations page
            logger.info(f"Opening MERX solicitations page: {self.base_url}")
            self.driver.get(self.base_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Check if we got a 404
            if "error 404" in self.driver.page_source.lower():
                logger.error("✗ Got 404 error - URL might be wrong again")
                if self.debug:
                    self.driver.save_screenshot("/tmp/merx_404.png")
                return all_results
            
            logger.info(f"✓ Page loaded: {self.driver.title}")
            
            # Perform search (or skip if no search box)
            self._perform_search(search_term)
            
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
    
    def save_results(self, results: List[Dict], filename: str = "/tmp/merx_results.json"):
        """
        Save results to a JSON file.
        
        Args:
            results: List of solicitation dictionaries
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
    print("MERX Solicitations Scraper - Enhanced Version")
    print("URL: https://www.merx.com/public/solicitations/open")
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
    print(f"SCRAPING COMPLETE - Found {len(results)} solicitations")
    print("="*70 + "\n")
    
    for i, sol in enumerate(results, 1):
        print(f"{i}. {sol['title'][:70]}")
        print(f"   Organization: {sol['organization'][:50]}")
        print(f"   Published: {sol['published_date']}")
        print(f"   Closes: {sol['closing_date']}")
        print(f"   Link: {sol['link']}")
        print()
    
    # Save results
    if results:
        scraper.save_results(results)
        print(f"\n✓ Full results saved to /tmp/merx_results.json")
        
        # Show sample JSON structure
        print("\nSample JSON structure:")
        print(json.dumps(results[0] if results else {}, indent=2))
    else:
        print("\n⚠ No results to save")
        print("\nPossible reasons:")
        print("1. Page structure has changed - check screenshots in /tmp/")
        print("2. No solicitations match your search term")
        print("3. Page requires authentication")
    
    return results


if __name__ == "__main__":
    main()
