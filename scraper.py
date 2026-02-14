"""
MERX Scraper - Enhanced with Date Filter and Fixed Pagination
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
    
    def _extract_link_from_row(self, row) -> Optional[str]:
        """Extract the opportunity link from a row."""
        try:
            links = row.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute('href')
                if href and ('view-notice' in href or 'solicitation' in href):
                    return href
            if links:
                return links[0].get_attribute('href')
        except Exception as e:
            logger.debug(f"Error extracting link: {e}")
        return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Try to parse a date string into a datetime object."""
        if not date_str:
            return None
        
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%b %d, %Y',
            '%B %d, %Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%d-%m-%Y',
            '%m-%d-%Y',
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except:
                continue
        return None
    
    def _scrape_page(self, page_num: int) -> List[Dict]:
        """Scrape solicitations from the current page."""
        results = []
        
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
                row_text = row.text.strip()
                if not row_text:
                    continue
                
                link = self._extract_link_from_row(row)
                cols = row.find_elements(By.TAG_NAME, "td")
                
                if cols and len(cols) >= 3:
                    title = cols[0].text.strip() if len(cols) > 0 else ""
                    organization = cols[1].text.strip() if len(cols) > 1 else ""
                    
                    if len(cols) >= 4:
                        published_date = cols[2].text.strip()
                        closing_date = cols[3].text.strip()
                    elif len(cols) == 3:
                        published_date = ""
                        closing_date = cols[2].text.strip()
                    else:
                        published_date = ""
                        closing_date = cols[-1].text.strip()
                else:
                    lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                    title = lines[0] if len(lines) > 0 else row_text[:100]
                    organization = lines[1] if len(lines) > 1 else ""
                    published_date = ""
                    closing_date = ""
                    
                    for line in lines:
                        if any(char.isdigit() for char in line):
                            if not published_date and len(line) < 30:
                                published_date = line
                            elif not closing_date and len(line) < 30:
                                closing_date = line
                
                if title and len(title) > 5:
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
                    
                    if self.debug and idx < 5:
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
        """Navigate to the next page of results."""
        next_button_selectors = [
            "a.next",
            "button.next",
            "button[aria-label='Next page']",
            "button[aria-label='next']",
            ".pagination-next",
            "li.next a",
            "a[aria-label='Next']",
        ]
        
        for selector in next_button_selectors:
            try:
                next_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for next_button in next_buttons:
                    if not next_button.is_displayed():
                        continue
                    
                    # Check if disabled
                    disabled = next_button.get_attribute('disabled')
                    aria_disabled = next_button.get_attribute('aria-disabled')
                    classes = next_button.get_attribute('class') or ''
                    
                    if disabled or aria_disabled == 'true' or 'disabled' in classes.lower():
                        logger.info(f"Next button disabled (selector: {selector})")
                        continue
                    
                    logger.info(f"Found clickable next button (selector: {selector})")
                    
                    # Scroll and click
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    time.sleep(1)
                    
                    try:
                        next_button.click()
                    except:
                        # Try JavaScript click if normal click fails
                        self.driver.execute_script("arguments[0].click();", next_button)
                    
                    # Wait for page to load
                    logger.info("Waiting for next page to load...")
                    time.sleep(10)
                    
                    logger.info("✓ Clicked next page button")
                    return True
                    
            except NoSuchElementException:
                continue
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue
        
        logger.info("No more clickable next buttons found - reached last page")
        return False
    
    def scrape(self, search_term: str = "health", max_pages: int = 5, min_published_date: str = None) -> List[Dict]:
        """
        Scrape MERX solicitations.
        
        Args:
            search_term: The term to search for
            max_pages: Maximum number of pages to scrape
            min_published_date: Minimum published date (format: YYYY-MM-DD). Only collect opportunities published on or after this date.
            
        Returns:
            List of solicitation dictionaries
        """
        all_results = []
        
        # Parse minimum date if provided
        min_date_obj = None
        if min_published_date:
            try:
                min_date_obj = datetime.strptime(min_published_date, '%Y-%m-%d')
                logger.info(f"Filtering for opportunities published on or after: {min_published_date}")
            except Exception as e:
                logger.warning(f"Could not parse min_published_date '{min_published_date}': {e}")
        
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
                
                # Filter by date if min_date is specified
                if min_date_obj:
                    filtered_results = []
                    for result in page_results:
                        published_str = result.get('published_date', '')
                        if published_str:
                            # Try to parse the published date
                            published_date_obj = self._parse_date(published_str)
                            if published_date_obj:
                                # Only include if published on or after min_date
                                if published_date_obj >= min_date_obj:
                                    filtered_results.append(result)
                                else:
                                    logger.debug(f"Filtered out: {result['title'][:40]} (published: {published_str})")
                            else:
                                # Can't parse date, include it to be safe
                                filtered_results.append(result)
                        else:
                            # No published date, include it
                            filtered_results.append(result)
                    
                    logger.info(f"After date filtering: {len(filtered_results)} of {len(page_results)} opportunities matched")
                    all_results.extend(filtered_results)
                else:
                    # No date filter, include all
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
    
    # Get parameters from environment variables (for GitHub Actions)
    search_term = os.getenv('SEARCH_TERM', 'health')
    max_pages = int(os.getenv('MAX_PAGES', '5'))
    min_published_date = os.getenv('MIN_PUBLISHED_DATE', None)  # Format: YYYY-MM-DD
    
    if min_published_date:
        print(f"Filtering for opportunities published on or after: {min_published_date}")
    
    # Initialize scraper
    scraper = MERXScraper(
        headless=True,  # Set to False to see the browser
        debug=True      # Enable debug mode
    )
    
    # Run scraper
    results = scraper.scrape(
        search_term=search_term,
        max_pages=max_pages,
        min_published_date=min_published_date
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
        print("3. Date filter is too restrictive")
    
    return results


if __name__ == "__main__":
    main()
