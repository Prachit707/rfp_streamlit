import time
import csv
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


OUTPUT_FILE = "rfp_results.csv"
MAX_PAGES = 7


# =========================
# DRIVER SETUP
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
# SCRAPER
# =========================

def scrape_merx():

    driver = setup_driver()
    wait = WebDriverWait(driver, 30)

    results = []

    try:

        print("Opening MERX homepage...")
        driver.get("https://www.merx.com")

        time.sleep(5)

        print("Opening Canadian Public Opportunities...")

        canadian = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//a[contains(@href,'/public/solicitations')]"
        )))

        driver.execute_script("arguments[0].click();", canadian)

        time.sleep(5)

        # =========================
        # TARGET CORRECT SEARCH BOX
        # =========================

        print("Locating active search box...")

        search_box = wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "//form//input[@type='text' and not(@disabled)]"
        )))

        # force focus via JS
        driver.execute_script("""
            arguments[0].focus();
            arguments[0].value = '';
        """, search_box)

        time.sleep(1)

        print("Typing health...")

        search_box.send_keys("health")
        search_box.send_keys(Keys.ENTER)

        time.sleep(5)


        # =========================
        # PAGE LOOP
        # =========================

        for page in range(1, MAX_PAGES + 1):

            print(f"Scanning page {page}")

            wait.until(EC.presence_of_all_elements_located((
                By.XPATH,
                "//a[contains(@class,'solicitation-link')]"
            )))

            cards = driver.find_elements(
                By.XPATH,
                "//a[contains(@class,'solicitation-link')]"
            )

            print("Cards found:", len(cards))

            for card in cards:

                try:

                    title = card.find_element(
                        By.XPATH,
                        ".//span[contains(@class,'rowTitle')]"
                    ).text.strip()

                    link = card.get_attribute("href")

                    published = card.find_element(
                        By.XPATH,
                        ".//span[contains(@class,'publicationDate')]//span"
                    ).text.strip()

                    results.append({
                        "title": title,
                        "published": published,
                        "link": link
                    })

                except:
                    continue


            # NEXT PAGE
            if page < MAX_PAGES:

                try:

                    next_button = wait.until(EC.element_to_be_clickable((
                        By.XPATH,
                        "//a[contains(@class,'next')]"
                    )))

                    driver.execute_script(
                        "arguments[0].click();",
                        next_button
                    )

                    time.sleep(5)

                except:

                    print("No more pages")
                    break


    finally:

        driver.quit()

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

    data = scrape_merx()

    save_results(data)

    print("Done")
