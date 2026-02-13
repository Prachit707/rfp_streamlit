import streamlit as st
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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from transformers import pipeline

# =====================================
# STREAMLIT UI
# =====================================

st.set_page_config(page_title="MERX Health IT Opportunity Finder", layout="wide")

st.title("MERX Health IT Opportunity Finder")

min_date_input = st.date_input("Select minimum posted date")

confidence_threshold = 0.5

run_button = st.button("Run Scraper")

# =====================================
# MAIN EXECUTION
# =====================================

if run_button:

    min_date = datetime.combine(min_date_input, datetime.min.time())

    st.write("Starting scraping...")

    # =====================================
    # HEADLESS CHROME SETUP (IMPORTANT)
    # =====================================

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

        # Click Canadian Tenders
        wait.until(EC.element_to_be_clickable((
            By.XPATH,
            "/html/body/header/div[3]/div/ul/li[2]/div[2]/div/nav/div/div/div/nav/ul/li[1]/a"
        ))).click()

        time.sleep(3)

        # Search "health"
        search_box = wait.until(EC.presence_of_element_located((
            By.XPATH,
            "/html/body/main/div[1]/div/form/div[1]/div/div[1]/div/input"
        )))

        search_box.clear()
        search_box.send_keys("health")
        search_box.send_keys(Keys.ENTER)

        time.sleep(3)

        # Select Open Solicitations
        status_dropdown = Select(wait.until(EC.presence_of_element_located((
            By.XPATH,
            "/html/body/main/div[1]/div/form/div[1]/div/div[5]/select"
        ))))

        status_dropdown.select_by_visible_text("Open Solicitations")

        time.sleep(3)

        progress_bar = st.progress(0)

        # =====================================
        # SCRAPE 7 PAGES
        # =====================================

        for page in range(1, 8):

            st.write(f"Scanning Page {page}...")

            progress_bar.progress(page / 7)

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

                    if post_date < min_date:
                        continue

                    # Open detail page
                    driver.execute_script("window.open(arguments[0]);", link)
                    driver.switch_to.window(driver.window_handles[1])

                    time.sleep(2)

                    try:
                        description = driver.find_element(
                            By.ID, "descriptionText"
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

            # Next page
            if page < 7:
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

    st.write(f"Total scraped: {len(entries)}")

    if not entries:
        st.error("No opportunities found")
        st.stop()

    # =====================================
    # CLASSIFICATION
    # =====================================

    st.write("Loading AI classification model...")

    classifier = pipeline(
        "zero-shot-classification",
        model="valhalla/distilbart-mnli-12-3",
        device=0 if torch.cuda.is_available() else -1
    )

    df = pd.DataFrame(entries)

    df["Text"] = df["Title"].fillna("") + ". " + df["Description"].fillna("")

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

    st.write("Classifying opportunities...")

    for text in df["Text"]:

        text = str(text)[:1000]

        result = classifier(text, candidate_labels)

        label = result["labels"][0]
        score = result["scores"][0]

        if label == "Hardware/Instrument Requirement":
            final_label = "Not Eligible (Hardware)"
        else:
            final_label = label

        predicted_labels.append(final_label)
        confidence_scores.append(round(score, 3))

    df["Predicted_Category"] = predicted_labels
    df["Confidence"] = confidence_scores

    # =====================================
    # FILTERING
    # =====================================

    df = df[
        (df["Predicted_Category"] != "Not Eligible (Hardware)") &
        (df["Confidence"] >= confidence_threshold)
    ]

    st.success(f"Final retained opportunities: {len(df)}")

    # =====================================
    # DISPLAY RESULTS
    # =====================================

    st.dataframe(df, use_container_width=True)

    # =====================================
    # DOWNLOAD BUTTON
    # =====================================

    filename = f"MERX_Health_IT_Filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

    df.to_excel(filename, index=False)

    with open(filename, "rb") as file:
        st.download_button(
            label="Download Excel",
            data=file,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
