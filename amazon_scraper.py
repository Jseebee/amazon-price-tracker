"""
Amazon Price Tracker – GitHub Actions version
---------------------------------------------
Reads product URLs from your Google Sheet,
collects current price & title from each Amazon page,
and updates the same sheet automatically.

Works with service_key.json credentials stored in GitHub Secrets.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import os


# === Google Sheets authentication ===
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"
         "https://www.googleapis.com/auth/drive"]
SERVICE_FILE = "service_key.json"
SHEET_NAME = os.environ.get("SHEET_NAME", "Amazon Price Tracker Master")

creds = Credentials.from_service_account_file(SERVICE_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
sheet = client.open("1i1eeHJ6iwJFsh1EpfqnxGrHEw6K6pfRZ7QAcMxJCOoA").worksheet("Data")

# Optional: set User‑Agent string to reduce blocking
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0 Safari/537.36"
    )
}


def clean_price(text):
    """Extract float from price string like '£19.99'."""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d{1,2})?)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def get_price_and_title(url):
    """Fetch title and price from Amazon product page."""
    if not url or "amazon" not in url:
        return None, None

    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Try multiple selectors to survive layout changes
        title_tag = soup.find(id="productTitle") or soup.find("span", {"data-testid": "title"})
        title = title_tag.get_text(strip=True) if title_tag else ""

        price_tag = (
            soup.find("span", id="priceblock_ourprice")
            or soup.find("span", id="priceblock_dealprice")
            or soup.select_one("span.a-price span.a-offscreen")
        )
        price = clean_price(price_tag.get_text()) if price_tag else None

        return title, price

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, None


# === Main processing loop ===
records = sheet.get_all_records()
for i, row in enumerate(records, start=2):  # start=2 to skip header row
    url = row.get("Amazon Link") or ""
    current_prev = row.get("Current Price (£)")
    if not url:
        continue

    title, price = get_price_and_title(url)
    if not title and not price:
        continue

    if title:
        sheet.update_cell(i, 1, title)  # Item Name
    if price is not None and price != current_prev:
        sheet.update_cell(i, 6, price)  # Column F = Current Price (£)

    print(f"[{i}] Updated: {title or 'N/A'} – £{price if price else '??'}")
    time.sleep(2)  # polite delay so Amazon doesn’t block

print("✅ Done – Sheet updated.")
