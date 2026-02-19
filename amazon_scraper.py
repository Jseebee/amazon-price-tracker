"""
Amazon Price Tracker (GitHub Actions Ready)
------------------------------------------
Scrapes product titles & prices from Amazon
and updates a Google Sheet (tab: Data).
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

# Your Sheet info
SHEET_ID = "1i1eeHJ6iwJFsh1EpfqnxGrHEw6K6pfRZ7QAcMxJCOoA"   # replace if you duplicate the sheet
WORKSHEET_NAME = "Data"

creds = Credentials.from_service_account_file(SERVICE_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
print("✅ Connected to Google Sheet")


# === Amazon scraping setup ===
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    )
}


def clean_price(text: str):
    """Extracts numeric value from Amazon price text."""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d{1,2})?)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def get_price_and_title(url):
    """Fetch title and price safely from an Amazon URL."""
    if not url or "amazon" not in url.lower():
        return None, None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title_tag = soup.find(id="productTitle")
        price_tag = (
            soup.find("span", id="priceblock_ourprice")
            or soup.find("span", id="priceblock_dealprice")
            or soup.select_one("span.a-price span.a-offscreen")
        )

        title = title_tag.get_text(strip=True) if title_tag else ""
        price = clean_price(price_tag.get_text()) if price_tag else None

        return title, price

    except Exception as e:
        print(f"⚠️  Error scraping {url[:60]}: {e}")
        return None, None


# === Main update loop ===
records = sheet.get_all_records()  # assumes headers in row 1
print(f"🧮  Found {len(records)} rows to check")

for i, row in enumerate(records, start=2):  # data starts on row 2
    url = row.get("Amazon Link") or ""
    if not url:
        continue

    title, price = get_price_and_title(url)
    if not title and price is None:
        continue

    if title:
        sheet.update_cell(i, 1, title)  # Item Name (A)
    if price is not None:
        sheet.update_cell(i, 6, price)  # Col F (Current Price £)
        print(f"✅ Row {i} → {title[:40]} … £{price}")

    time.sleep(2)  # polite delay

print("🎯 All done – Sheet updated successfully.")
