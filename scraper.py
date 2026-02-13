import time
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# CONFIG
# =========================

OUTPUT_FILE = "rfp_results.csv"
MERX_URL = "https://www.merx.com"


# =========================
# DRIVER SETUP (GitHub Actions Safe)
# =========================

def setup_driver():

    chrome_options = Options()

    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    )

    driver = webdriver.Chrome(options=chrome_options)

    return driver


# =========================
# SAFE GET FUNCTION
# =========================

def safe_get(driver, url):

    print(f"Opening {url}")

    driver.get(url)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    time.sleep(3)


# =========================
# SCRAPE MERX
# =========================

def scrape_merx(driver):

    results = []

    try:

        safe_get(driver, MERX_URL)

        print("Looking for opportunities...")

        # wait for links to load
        links = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "a"))
        )

        for link in links:

            text = link.text.strip()
            href = link.get_attribute("href")

            if text and href and "opportunity" in href.lower():

                results.append({
                    "title": text,
                    "url": href,
                    "source": "MERX",
                    "date": datetime.now().strftime("%Y-%m-%d")
                })

    except Exception as e:

        print("MERX scraping failed:", e)

    return results


# =========================
# SAVE CSV
# =========================

def save_results(results):

    if not results:
        print("No results found")
        return

    keys = results[0].keys()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(results)

    print(f"Saved {len(results)} results")


# =========================
# MAIN
# =========================

if __name__ == "__main__":

    driver = setup_driver()

    all_results = []

    try:

        merx_results = scrape_merx(driver)
        all_results.extend(merx_results)

    finally:

        driver.quit()

    save_results(all_results)

    print("Done")
