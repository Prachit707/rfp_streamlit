import time
import os
from datetime import datetime
import pandas as pd
import torch
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from transformers import pipeline


# =====================================
# CONFIGURATION
# =====================================

MIN_DATE_STR = "01-01-2026"   # change as needed
MIN_DATE = datetime.strptime(MIN_DATE_STR, "%d-%m-%Y")

CONFIDENCE_THRESHOLD = 0.5

MAX_PAGES = 7


# =====================================
# HEADLESS CHROME SETUP (GitHub Actions Compatible)
# =====================================

options = webdriver.ChromeOptions()

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)


entries = []


# =====================================
# OPEN MERX
# =====================================

print("Opening MERX...")
driver.get("https://www.merx.com")

time.sleep(3)


# =====================================
# CLICK CANADIAN TENDERS
# =====================================

wait.until(EC.element_to_be_clickable((
    By.XPATH,
    "/html/body/header/div[3]/div/ul/li[2]/div[2]/div/nav/div/div/div/nav/ul/li[1]/a"
))).click()

time.sleep(3)


# =====================================
# SEARCH FOR "health"
# =====================================

search_box = wait.until(EC.presence_of_element_located((
    By.XPATH,
    "/html/body/main/div[1]/div/form/div[1]/div/div[1]/div/input"
)))

search_box.clear()
search_box.send_keys("health")
search_box.submit()

time.sleep(3)


# =====================================
# SELECT OPEN SOLICITATIONS
# =====================================

status_dropdown = Select(wait.until(EC.presence_of_element_located((
    By.XPATH,
    "/html/body/main/div[1]/div/form/div[1]/div/div[5]/select"
))))

status_dropdown.select_by_visible_text("Open Solicitations")

time.sleep(3)


# =====================================
# SCRAPE PAGES
# =====================================

print("Scraping opportunities...")

for page in range(1, MAX_PAGES + 1):

    print(f"Page {page}")

    wait.until(EC.presence_of_element_located((
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


            # OPEN DETAILS PAGE

            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])

            time.sleep(2)

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


        except Exception as e:
            continue


    # NEXT PAGE

    if page < MAX_PAGES:

        try:

            next_button = driver.find_element(
                By.XPATH,
                "/html/body/main/div[1]/div/form/div[2]/div[2]/div/div[3]/a"
            )

            driver.execute_script(
                "arguments[0].click();",
                next_button
            )

            time.sleep(3)

        except:
            break


driver.quit()

print(f"Total scraped: {len(entries)}")


if not entries:

    print("No opportunities found.")
    exit()


# =====================================
# CLASSIFICATION
# =====================================

print("Loading classification model...")

classifier = pipeline(

    "zero-shot-classification",

    model="valhalla/distilbart-mnli-12-3",

    device=0 if torch.cuda.is_available() else -1

)


candidate_labels = [

    "IT Services",
    "IT Solutions",
    "IT Product",
    "IT Consultancy",
    "AI-Based Opportunity",
    "Hardware/Instrument Requirement"

]


df = pd.DataFrame(entries)

df["Text"] = df["Title"].fillna("") + ". " + df["Description"].fillna("")


print("Classifying...")

predicted_labels = []
confidence_scores = []


for text in tqdm(df["Text"]):

    text = str(text)[:1000]

    result = classifier(text, candidate_labels)

    label = result["labels"][0]
    score = result["scores"][0]

    if label == "Hardware/Instrument Requirement":

        predicted_labels.append("Not Eligible (Hardware)")

    else:

        predicted_labels.append(label)

    confidence_scores.append(round(score, 3))


df["Predicted_Category"] = predicted_labels
df["Confidence"] = confidence_scores


# =====================================
# FILTER FINAL OUTPUT
# =====================================

df = df[

    (df["Predicted_Category"] != "Not Eligible (Hardware)") &

    (df["Confidence"] >= CONFIDENCE_THRESHOLD)

]


print(f"Final opportunities retained: {len(df)}")


# =====================================
# SAVE FILE
# =====================================

filename = "MERX_Health_IT_Filtered.xlsx"

df.to_excel(filename, index=False)


print("Saved:", filename)
print("Path:", os.path.abspath(filename))
