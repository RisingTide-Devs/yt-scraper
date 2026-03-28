"""
scrapers/twitterScraper.py — scrape a Twitter/X profile page using Playwright.

Requires:
    pip install playwright
    playwright install chromium

Usage:
    python scrapers/twitterScraper.py <handle>
"""

import re
import sys
import os
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(__file__))
from regexHandler import extract, clean_handle

PLATFORM = "twitter_x"
DELAY = 3000  # ms to wait for JS to render

GITHUB_NOISE = ["mozilla", "tailwindlabs", "mozdevs", "jensimmons"]


def fetch(handle):
    url = f"https://x.com/{handle}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(DELAY)
        html = page.content()
        browser.close()
    return url, html


def scrape(handle):
    handle = clean_handle(handle)
    url, html = fetch(handle)
    contacts = extract(html, exclude_platform=PLATFORM)
    # Filter GitHub noise specific to X's page
    contacts["github"] = [
        m for m in contacts.get("github", [])
        if not any(noise in m.lower() for noise in GITHUB_NOISE)
    ]
    return handle, url, contacts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrapers/twitterScraper.py <handle>")
        sys.exit(1)
    handle, url, contacts = scrape(sys.argv[1])
    print(f"URL: {url}")
    for platform, matches in contacts.items():
        if matches:
            print(f"  {platform}: {', '.join(matches)}")