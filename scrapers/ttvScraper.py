"""
scrapers/twitch.py — scrape a twitch profile page.

Usage:
    python scrapers/twitch.py <handle>
"""

import re
import sys
import requests
from formats import SOCIAL_PATTERNS, PLATFORM_DOMAINS

PLATFORM = "twitch"
DELAY = 1.5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return requests.utils.unquote(resp.text)


def clean_handle(raw):
    h = re.sub(r"https?://(?:www\.)?[^/]+/", "", raw)
    h = re.sub(r"^(?:www\.)?[^/]+/", "", h)
    h = h.strip("/").lstrip("@")
    h = re.sub(r"[.\u2026]+$", "", h)
    h = h.rstrip("_-")
    return h.lower()


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
    url = "https://www.twitch.tv/{handle}/about".replace("{handle}", handle)
    html = fetch(url)
    contacts = extract(html)
    return handle, url, contacts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scrapers/twitch.py <handle>")
        sys.exit(1)
    handle, url, contacts = scrape(sys.argv[1])
    print(f"URL: {url}")
    for platform, matches in contacts.items():
        if matches:
            print(f"  {platform}: {', '.join(matches)}")
