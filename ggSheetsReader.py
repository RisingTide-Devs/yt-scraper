"""
sheetReader.py — reads a Google Sheet, skips yellow-highlighted rows,
and outputs a channels.txt file of URLs for orchestrator.py to scrape.

Usage:
    python sheetReader.py

Requirements:
    pip install google-auth google-auth-httplib2 google-api-python-client python-dotenv
"""

import os
import sys
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SHEET_ID               = os.getenv("SHEET_ID")
SHEET_NAME             = os.getenv("SHEET_NAME", "Sheet1")
SERVICE_ACCOUNT_FILE   = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
OUTPUT_FILE            = os.getenv("OUTPUT_FILE", "channels.txt")

# Yellow 3 RGB thresholds (normalized 0-1). Rows matching this color are skipped.
YELLOW_R = float(os.getenv("YELLOW_R", 1.0))
YELLOW_G = float(os.getenv("YELLOW_G", 0.839))
YELLOW_B = float(os.getenv("YELLOW_B", 0.4))
COLOR_TOLERANCE = 0.05  # Allow slight variation in color values

# URL columns (0-indexed): Tiktok=5, Youtube=6, Twitch=7, Facebook=8, Twitter/X=9, Instagram=10
URL_COLS = [5, 6, 7, 8, 9, 10]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def is_yellow(color):
    """Check if a color dict matches Google Sheets Yellow 3."""
    if not color:
        return False
    r = color.get("red", 0)
    g = color.get("green", 0)
    b = color.get("blue", 0)
    return (
        abs(r - YELLOW_R) <= COLOR_TOLERANCE and
        abs(g - YELLOW_G) <= COLOR_TOLERANCE and
        abs(b - YELLOW_B) <= COLOR_TOLERANCE
    )


def get_sheet_data(service):
    """Fetch all cell data including background colors from the sheet."""
    sheet_range = f"{SHEET_NAME}"
    result = service.spreadsheets().get(
        spreadsheetId=SHEET_ID,
        ranges=[sheet_range],
        includeGridData=True,
        fields="sheets(data(rowData(values(userEnteredValue,effectiveFormat(backgroundColor)))))"
    ).execute()

    return result["sheets"][0]["data"][0]["rowData"]


def extract_urls(row_data):
    """Extract all URLs from a row's cells."""
    urls = []
    for col_idx in URL_COLS:
        if col_idx >= len(row_data):
            continue
        cell = row_data[col_idx]
        val = cell.get("userEnteredValue", {}).get("stringValue", "")
        if val.startswith("http"):
            urls.append(val.strip())
    return urls


def main():
    if not SHEET_ID:
        print("Error: SHEET_ID not set in .env")
        sys.exit(1)

    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"Error: Service account file not found: {SERVICE_ACCOUNT_FILE}")
        sys.exit(1)

    print(f"Connecting to Google Sheets...")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)

    print(f"Reading sheet: {SHEET_NAME}...")
    rows = get_sheet_data(service)

    all_urls = []
    skipped = 0
    total_data_rows = 0

    # Skip header rows (rows 0 and 1)
    for row in rows[2:]:
        row_data = row.get("values", [])
        if not row_data:
            continue

        total_data_rows += 1

        # Check if the first cell is yellow highlighted
        first_cell = row_data[0] if row_data else {}
        bg_color = first_cell.get("effectiveFormat", {}).get("backgroundColor", {})

        if is_yellow(bg_color):
            skipped += 1
            continue

        urls = extract_urls(row_data)
        all_urls.extend(urls)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = [u for u in all_urls if not (u in seen or seen.add(u))]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for url in unique_urls:
            f.write(url + "\n")

    print(f"\nDone.")
    print(f"  Total data rows:   {total_data_rows}")
    print(f"  Skipped (yellow):  {skipped}")
    print(f"  URLs found:        {len(all_urls)}")
    print(f"  Unique URLs:       {len(unique_urls)}")
    print(f"  Written to:        {OUTPUT_FILE}")
    print(f"\nRun: python orchestrator.py {OUTPUT_FILE}")


if __name__ == "__main__":
    main()