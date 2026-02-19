"""
Amazon Price Tracker – DEBUG build
Checks Amazon product pages and updates the Google Sheet.
Includes partial HTML print for the first product to confirm response content.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials


# === Google Sheets connection ===
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_FILE = "service_key.json"
SHEET_ID = "1i1eeHJ6iwJFsh1EpfqnxGrHEw6K6pfRZ7QAcMxJCOoA"   # your Sheet ID
WORKSHEET_NAME = "Data"

creds = Credentials.from_service_account_file(SERVICE_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
print("✅ Connected to Google Sheet")

# === Headers (pretend to be a normal browser) ===
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    )
}


def clean_price(text: str):
    """Extract numeric £ value from text."""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d{1,2})?)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def get_price_and_title(url, row_index):
    """Fetch title and price, print sample HTML for one row to debug."""
    if not url or "amazon" not in url.lower():
        return None, None

    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
        resp.raise_for_status()

        # ---- DEBUG: show start of page for first row only ----
        if row_index == 2:
            print(f"\n🔍 Sample HTML (first 800 chars from Amazon response)\n{'-'*60}")
            print(resp.text[:800])
            print("\n------------------------------------------------------------\n")

        soup = BeautifulSoup(resp.text, "html.parser")

        title_tag = soup.find(id="productTitle")
        title = title_tag.get_text(strip=True) if title_tag else ""

        price_tag = (
            soup.select_one("span.a-price.aok-align-center span.a-offscreen")
            or soup.select_one("span[data-a-color='price'] span.a-offscreen")
            or soup.select_one("span.a-price > span.a-offscreen")
        )

        price = clean_price(price_tag.get_text()) if price_tag else None
        return title, price

    except Exception as e:
        print(f"⚠️ Error scraping {url[:70]}: {e}")
        return None, None


# === Main loop ===
records = sheet.get_all_records()
print(f"🧮 Found {len(records)} rows to check")

updated_count = 0

for i, row in enumerate(records, start=2):
    url = row.get("Amazon Link") or ""
    if not url:
        continue

    title, price = get_price_and_title(url, i)

    if title:
        sheet.update_cell(i, 1, title)  # Item Name
    if price is not None:
        sheet.update_cell(i, 6, price)  # Current Price (£)
        updated_count += 1
        print(f"✅ Row {i} → {title[:40]} … £{price}")

    time.sleep(2)

print(f"🎯 All done – {updated_count} rows updated.")
