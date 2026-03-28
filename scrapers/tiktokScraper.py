"""
scrapers/tiktokScraper.py — scrape a TikTok profile page.

Usage:
    python scrapers/tiktokScraper.py <handle>
"""

import re
import sys
import requests
from regexHandler import extract, clean_handle

PLATFORM = "tiktok"
DELAY = 1.5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return requests.utils.unquote(resp.text)


def scrape(handle):
    handle = clean_handle(handle)
    url = f"https://www.tiktok.com/@{handle}"
    html = fetch(url)
    contacts = extract(html, exclude_platform=PLATFORM)
    return handle, url, contacts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrapers/tiktokScraper.py <handle>")
        sys.exit(1)
    handle, url, contacts = scrape(sys.argv[1])
    print(f"URL: {url}")
    for platform, matches in contacts.items():
        if matches:
            print(f"  {platform}: {', '.join(matches)}")