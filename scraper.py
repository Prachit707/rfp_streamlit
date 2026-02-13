import time
from datetime import datetime
import pandas as pd
import torch
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from transformers import pipeline

# ==============================
# SETTINGS
# ==============================

MIN_DATE = datetime(2024, 1, 1)
confidence_threshold = 0.5

# ==============================
# DRIVER (HEADLESS)
# ==============================

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

wait = WebDriverWait(driver, 20)

entries = []

try:
    driver.get("https://www.merx.com")

    wait.until(EC.element_to_be_clickable((
        By.XPATH,
        "/html/body/header/div[3]/div/ul/li[2]/div[2]/div/nav/div/div/div/nav/ul/li[1]/a"
    ))).click()

    time.sleep(3)

    search_box = wait.until(EC.presence_of_element_located((
        By.XPATH,
        "/html/body/main/div[1]/div/form/div[1]/div/div[1]/div/input"
    )))

    search_box.send_keys("health")
    search_box.send_keys(Keys.ENTER)

    time.sleep(3)

    status_dropdown = Select(wait.until(EC.presence_of_element_located((
        By.XPATH,
        "/html/body/main/div[1]/div/form/div[1]/div/div[5]/select"
    ))))

    status_dropdown.select_by_visible_text("Open Solicitations")

    time.sleep(3)

    for page in range(1, 4):

        wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//a[contains(@class,'solicitation-link')]"
        )))

        cards = driver.find_elements(
            By.XPATH,
            "//a[contains(@class,'solicitation-link')]"
        )

        for card in cards:
            try:
                title = card.text.strip()
                link = card.get_attribute("href")

                published = card.find_element(
                    By.XPATH,
                    ".//span[contains(@class,'publicationDate')]//span[@class='dateValue']"
                ).text.strip()

                post_date = datetime.strptime(published, "%Y/%m/%d")

                if post_date < MIN_DATE:
                    continue

                entries.append({
                    "Title": title,
                    "Link": link,
                    "Published Date": published
                })

            except:
                continue

        try:
            next_button = driver.find_element(
                By.XPATH,
                "/html/body/main/div[1]/div/form/div[2]/div[2]/div/div[3]/a"
            )
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
        except:
            break

finally:
    driver.quit()

if not entries:
    print("No data scraped")
    exit()

df = pd.DataFrame(entries)

# ==============================
# AI CLASSIFICATION
# ==============================

classifier = pipeline(
    "zero-shot-classification",
    model="valhalla/distilbart-mnli-12-3",
    device=-1
)

candidate_labels = [
    "IT Services",
    "IT Solutions",
    "IT Product",
    "IT Consultancy",
    "AI-Based Opportunity",
    "Hardware/Instrument Requirement"
]

predicted_labels = []
confidence_scores = []

for text in df["Title"]:
    result = classifier(text, candidate_labels)
    predicted_labels.append(result["labels"][0])
    confidence_scores.append(result["scores"][0])

df["Category"] = predicted_labels
df["Confidence"] = confidence_scores

df = df[df["Confidence"] >= confidence_threshold]

df.to_csv("output.csv", index=False)

print("Saved output.csv")

