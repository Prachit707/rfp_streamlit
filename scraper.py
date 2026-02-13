import time
import os
from datetime import datetime
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

from transformers import pipeline

# =====================================
# CONFIG
# =====================================

MIN_DATE = datetime(2026, 1, 1)   # change or pass dynamically later
MAX_PAGES = 7
CONFIDENCE_THRESHOLD = 0.5

entries = []

# =====================================
# STEALTH CHROME SETUP
# =====================================

options = webdriver.ChromeOptions()

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

options.add_argument("--window-size=1920,1080")

options.add_argument("--disable-blink-features=AutomationControlled")

options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

driver = webdriver.Chrome(options=options)

# hide webdriver flag
driver.execute_script(
    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
)

wait = WebDriverWait(driver, 30)

# =====================================
# OPEN MERX
# =====================================

print("Opening MERX...")

driver.get("https://www.merx.com")

wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
time.sleep(5)

# =====================================
# CLICK CANADIAN TENDERS
# =====================================

print("Opening Canadian Tenders...")

canadian = wait.until(EC.presence_of_element_located((
    By.XPATH,
    "//a[contains(text(),'Canadian Tenders')]"
)))

driver.execute_script("arguments[0].click();", canadian)

time.sleep(5)

# =====================================
# SEARCH HEALTH
# =====================================

print("Searching health...")

search_box = wait.until(EC.presence_of_element_located((
    By.XPATH,
    "//input[contains(@type,'text')]"
)))

search_box.clear()
search_box.send_keys("health")
search_box.send_keys(Keys.ENTER)

time.sleep(5)

# =====================================
# SELECT OPEN SOLICITATIONS
# =====================================

print("Filtering Open Solicitations...")

dropdown = wait.until(EC.presence_of_element_located((
    By.XPATH,
    "//select"
)))

Select(dropdown).select_by_visible_text("Open Solicitations")

time.sleep(5)

# =====================================
# SCRAPE PAGES
# =====================================

print("Scraping pages...")

for page in range(1, MAX_PAGES + 1):

    print(f"Page {page}")

    wait.until(EC.presence_of_all_elements_located((
        By.XPATH,
        "//a[contains(@class,'solicitation-link')]"
    )))

    cards = driver.find_elements(
        By.XPATH,
        "//a[contains(@class,'solicitation-link')]"
    )

    print("Found:", len(cards))

    for card in cards:

        try:

            title = card.find_element(
                By.XPATH,
                ".//span[contains(@class,'rowTitle')]"
            ).text.strip()

            link = card.get_attribute("href")

            if link.startswith("/"):
                link = "https://www.merx.com" + link

            published = card.find_element(
                By.XPATH,
                ".//span[contains(@class,'publicationDate')]//span[@class='dateValue']"
            ).text.strip()

            post_date = datetime.strptime(published, "%Y/%m/%d")

            if post_date < MIN_DATE:
                continue

            # OPEN DETAILS TAB
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])

            time.sleep(3)

            try:
                description = driver.find_element(
                    By.ID,
                    "descriptionText"
                ).text.strip()
            except:
                description = ""

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            entries.append({
                "Title": title,
                "Link": link,
                "Published Date": published,
                "Description": description
            })

        except:
            continue

    # NEXT PAGE
    if page < MAX_PAGES:

        try:

            next_button = wait.until(EC.presence_of_element_located((
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


driver.quit()

print("Total scraped:", len(entries))

if len(entries) == 0:
    print("No data found")
    exit()

# =====================================
# CLASSIFICATION
# =====================================

print("Loading classifier...")

classifier = pipeline(
    "zero-shot-classification",
    model="valhalla/distilbart-mnli-12-3"
)

candidate_labels = [
    "IT Services",
    "IT Solutions",
    "IT Product",
    "IT Consultancy",
    "AI-Based Opportunity",
    "Hardware Requirement"
]

df = pd.DataFrame(entries)

df["Text"] = df["Title"] + ". " + df["Description"]

predicted = []
scores = []

print("Classifying...")

for text in df["Text"]:

    text = text[:1000]

    result = classifier(text, candidate_labels)

    label = result["labels"][0]
    score = result["scores"][0]

    if label == "Hardware Requirement":
        predicted.append("Not Eligible")
    else:
        predicted.append(label)

    scores.append(score)

df["Category"] = predicted
df["Confidence"] = scores

# =====================================
# FILTER
# =====================================

df = df[
    (df["Category"] != "Not Eligible")
    &
    (df["Confidence"] >= CONFIDENCE_THRESHOLD)
]

print("Final count:", len(df))

# =====================================
# SAVE
# =====================================

filename = "MERX_Health_IT_Filtered.xlsx"

df.to_excel(filename, index=False)

print("Saved:", os.path.abspath(filename))
