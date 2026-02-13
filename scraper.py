import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape_merx():

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    print("Opening Canadian MERX opportunities page...")

    # DIRECT Canadian opportunities page (IMPORTANT)
    driver.get("https://www.merx.com/public/opportunities")

    # Wait until visible search box appears (ignore hidden inputs)
    print("Waiting for visible search box...")

    search_boxes = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='search']"))
    )

    search_box = None
    for box in search_boxes:
        if box.is_displayed():
            search_box = box
            break

    if search_box is None:
        raise Exception("No visible search box found")

    print("Typing 'health'...")

    search_box.click()
    search_box.send_keys("health")
    search_box.send_keys(Keys.ENTER)

    # Wait for results to load
    print("Waiting for results...")

    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
    )

    time.sleep(3)

    results = []

    page = 1
    MAX_PAGES = 3   # limit pages for testing

    while page <= MAX_PAGES:

        print(f"Scraping page {page}...")

        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

        for row in rows:
            try:
                cols = row.find_elements(By.TAG_NAME, "td")

                title = cols[0].text.strip()
                organization = cols[1].text.strip()
                closing_date = cols[3].text.strip()

                results.append({
                    "title": title,
                    "organization": organization,
                    "closing_date": closing_date,
                    "page": page
                })

            except:
                continue

        # next page
        try:
            next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next page']")

            if next_button.is_enabled():
                next_button.click()
                page += 1
                time.sleep(3)
            else:
                break

        except:
            break

    driver.quit()

    return results


if __name__ == "__main__":

    data = scrape_merx()

    print("\nRESULTS:\n")

    for item in data:
        print(item)
