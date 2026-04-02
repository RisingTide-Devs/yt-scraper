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
SERVICE_ACCOUNT_FILE   = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials.json")
OUTPUT_FILE            = os.getenv("OUTPUT_FILE", "channels.txt")

# Yellow color as returned by Google Sheets API for highlighted rows
YELLOW_R = 1.0
YELLOW_G = 0.9490
YELLOW_B = 0.8000
COLOR_TOLERANCE = 0.01

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


def get_sheet_data(service, sheet_name):
    """Fetch all cell data including background colors from the sheet."""
    result = service.spreadsheets().get(
        spreadsheetId=SHEET_ID,
        ranges=[sheet_name],
        includeGridData=True,
        fields="sheets(data(rowData(values(effectiveValue,effectiveFormat(backgroundColor)))))"
    ).execute()

    return result["sheets"][0]["data"][0]["rowData"]


# URL column priority order (0-indexed): Youtube=6, Twitch=7, TikTok=5, Facebook=8, Twitter/X=9, Instagram=10
URL_COLS_PRIORITY = [6, 7, 5, 8, 9, 10]


def extract_url(row_data):
    """Extract the first available URL from a row in priority order."""
    for col_idx in URL_COLS_PRIORITY:
        if col_idx >= len(row_data):
            continue
        cell = row_data[col_idx]
        val = cell.get("effectiveValue", {}).get("stringValue", "")
        if val.startswith("http"):
            return val.strip()
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python sheetReader.py <sheet_name>")
        print("  e.g. python sheetReader.py Sheet1")
        sys.exit(1)

    sheet_name = sys.argv[1]

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

    print(f"Reading sheet: {sheet_name}...")
    rows = get_sheet_data(service, sheet_name)

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

        url = extract_url(row_data)
        if url:
            all_urls.append(url)

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