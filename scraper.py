import time
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


OUTPUT_FILE = "merx_test_results.csv"
MAX_PAGES = 7


# ========================
# SETUP DRIVER (GitHub Safe)
# ========================

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


# ========================
# SAVE CSV
# ========================

def save_csv(data):

    if not data:
        print("No results found")
        return

    keys = data[0].keys()

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(data)

    print(f"Saved {len(data)} results to CSV")


# ========================
# SCRAPER
# ========================

def scrape_merx():

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    results = []

    print("Opening MERX...")
    driver.get("https://www.merx.com")

    time.sleep(5)

    print("Clicking Canadian Public Opportunities...")

    canadian = wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "//a[contains(text(),'Canadian Public Opportunities')]"
    )))

    canadian.click()

    time.sleep(5)

    print("Typing health in search...")

    search_box = wait.until(EC.presence_of_element_located((
        By.XPATH,
        "//input[contains(@placeholder,'Search')]"
    )))

    search_box.clear()
    search_box.send_keys("health")
    search_box.send_keys(Keys.ENTER)

    time.sleep(5)

    print("Selecting Open Solicitations...")

    status_dropdown = wait.until(EC.presence_of_element_located((
        By.XPATH,
        "//select"
    )))

    Select(status_dropdown).select_by_visible_text("Open Solicitations")

    time.sleep(5)


    # ========================
    # PAGE LOOP
    # ========================

    for page in range(1, MAX_PAGES + 1):

        print(f"Scanning Page {page}...")

        wait.until(EC.presence_of_all_elements_located((
            By.XPATH,
            "//a[contains(@class,'solicitation-link')]"
        )))

        cards = driver.find_elements(
            By.XPATH,
            "//a[contains(@class,'solicitation-link')]"
        )

        print(f"Found {len(cards)} opportunities")

        for card in cards:

            try:

                title = card.text.strip()

                link = card.get_attribute("href")

                try:
                    date = card.find_element(
                        By.XPATH,
                        ".//span[contains(@class,'dateValue')]"
                    ).text.strip()
                except:
                    date = "Unknown"

                print(title, "|", date)

                results.append({
                    "Title": title,
                    "Date": date,
                    "Link": link
                })

            except Exception as e:

                print("Error:", e)


        # Next page
        if page < MAX_PAGES:

            try:

                next_button = driver.find_element(
                    By.XPATH,
                    "//a[contains(@class,'next')]"
                )

                driver.execute_script(
                    "arguments[0].click();",
                    next_button
                )

                time.sleep(5)

            except:

                print("No more pages")
                break


    driver.quit()

    return results


# ========================
# MAIN
# ========================

if __name__ == "__main__":

    data = scrape_merx()

    save_csv(data)

    print("Done.")
