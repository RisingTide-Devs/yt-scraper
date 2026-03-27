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
from formats import SOCIAL_PATTERNS, PLATFORM_DOMAINS

PLATFORM = "twitter_x"
DELAY = 3000  # ms to wait for JS to render


def clean_handle(raw):
    h = re.sub(r"https?://", "", raw)          # strip protocol
    h = re.sub(r"(?:www\.)?(?:twitter|x)\.com/?", "", h, flags=re.I)  # strip domain
    h = h.strip("/").lstrip("@")
    h = re.sub(r"[.\u2026]+$", "", h)
    h = h.rstrip("_-")
    return h.lower()


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


def extract(html):
    own_domains = PLATFORM_DOMAINS.get(PLATFORM, [])
    results = {}
    for key, pattern in SOCIAL_PATTERNS.items():
        if key == PLATFORM:
            results[key] = []
            continue
        matches = re.findall(pattern, html, re.I)
        matches = [m for m in matches if not any(d in m.lower() for d in own_domains)]
        if key == "emails":
            matches = [m for m in matches if not re.search(r"youtube|google", m, re.I)]
        else:
            matches = [clean_handle(m) for m in matches]
            matches = [m for m in matches if m]
        seen = set()
        results[key] = [m for m in matches if not (m in seen or seen.add(m))]
    return results


def scrape(handle):
    handle = clean_handle(handle)
    url, html = fetch(handle)
    contacts = extract(html)
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