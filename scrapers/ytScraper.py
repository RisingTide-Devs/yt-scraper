import re
import csv
import sys
import time
import requests
from formats import SOCIAL_PATTERNS
from regexHandler import extract

OUTPUT_FILE = "youtube_contacts.csv"
DELAY = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_channels(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def scrape(channel):
    handle = channel if channel.startswith("@") else f"@{channel}"
    url = f"https://www.youtube.com/{handle}/about"

    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    html = requests.utils.unquote(resp.text)

    contacts = extract(html, exclude_platform="youtube")

    row = {"channel": channel, "url": url}
    for key, matches in contacts.items():
        row[key] = ", ".join(matches)

    return row


def main():
    if len(sys.argv) < 2:
        print("Usage: python ytScraper.py channels.txt")
        sys.exit(1)

    channels = load_channels(sys.argv[1])
    print(f"Loaded {len(channels)} channels from {sys.argv[1]}\n")

    rows = []
    for i, channel in enumerate(channels):
        print(f"[{i+1}/{len(channels)}] Scraping {channel}...")
        try:
            rows.append(scrape(channel))
        except Exception as e:
            print(f"  Failed: {e}")
            rows.append({"channel": channel, "url": "", "error": str(e)})
        if i < len(channels) - 1:
            time.sleep(DELAY)

    fields = ["channel", "url"] + list(SOCIAL_PATTERNS.keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()