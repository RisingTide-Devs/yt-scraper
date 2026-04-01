"""
orchestrator.py — scrape a list of social media links, following all discovered links across platforms.

Usage:
    python orchestrator.py channels.txt

channels.txt format — one URL per line, any supported platform:
    https://www.youtube.com/@MrBeast
    https://www.twitch.tv/clioaite
    https://x.com/parrot4chan

Adding a new platform:
    1. Create scrapers/<platform>.py with a scrape(handle) -> (handle, url, contacts) function
    2. Import it below and add an entry to PLATFORM_SCRAPERS
"""

import csv
import re
import sys
import time

from formats import SOCIAL_PATTERNS
import scrapers.ytScraper as youtube
import scrapers.twitterScraper as twitter_x
import scrapers.igScraper as instagram
import scrapers.tiktokScraper as tiktok
import scrapers.fbScraper as facebook
import scrapers.ttvScraper as twitch

OUTPUT_FILE = "contacts.csv"
DELAY = 1.5

# Maps platform key -> (scraper module, domain match strings)
PLATFORM_SCRAPERS = {
    "youtube":   (youtube,   ["youtube.com"]),
    "twitter_x": (twitter_x, ["twitter.com", "x.com"]),
    "instagram": (instagram, ["instagram.com"]),
    "tiktok":    (tiktok,    ["tiktok.com"]),
    "facebook":  (facebook,  ["facebook.com"]),
    "twitch":    (twitch,    ["twitch.tv"]),
}


def detect_platform(url):
    url_lower = url.lower()
    for platform, (scraper, domains) in PLATFORM_SCRAPERS.items():
        if any(d in url_lower for d in domains):
            return platform
    return None


def extract_handle(url):
    """Strip protocol and domain, return the bare handle/path preserving original case."""
    h = re.sub(r"https?://", "", url)
    h = re.sub(r"(?:www\.)?[^/]+\.[a-z]+/?", "", h, flags=re.I)
    h = h.strip("/").lstrip("@")
    return h


def load_urls(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def scrape_one(platform, handle):
    """Scrape a single handle and return (row, contacts dict)."""
    scraper, _ = PLATFORM_SCRAPERS[platform]

    if platform == "youtube":
        row = scraper.scrape(handle)
        row["source_platform"] = platform
        contacts = {k: [h.strip() for h in v.split(",") if h.strip()]
                    for k, v in row.items()
                    if k in SOCIAL_PATTERNS and v}
    else:
        p_handle, p_url, contacts = scraper.scrape(handle)
        row = {"source_platform": platform, "handle": p_handle, "url": p_url}
        for key, found in contacts.items():
            row[key] = ", ".join(found)

    return row, contacts


def scrape_seed(seed_url, writer):
    """
    Fully scrape a seed URL and all links it discovers.
    Writes rows directly to CSV as they complete.
    seen and scraped_channel_ids are local to this seed only.
    """
    platform = detect_platform(seed_url)
    if not platform:
        print(f"  [SKIP] Unrecognised URL: {seed_url}")
        return

    handle = extract_handle(seed_url)
    if not handle:
        return

    seen = {(platform, handle.lower())}
    scraped_channel_ids = set()
    stack = [(platform, handle)]

    while stack:
        current_platform, current_handle = stack.pop(0)

        # Skip channel/UC... if already scraped this seed
        if current_platform == "youtube" and current_handle.startswith("channel/"):
            channel_id = current_handle.split("/")[-1].upper()
            if channel_id in scraped_channel_ids:
                print(f"  [SKIP] Already scraped YouTube channel: {current_handle}")
                continue

        print(f"  [{current_platform}] Scraping: {current_handle}")

        try:
            row, contacts = scrape_one(current_platform, current_handle)

            if current_platform == "youtube" and "channel_id" in row:
                scraped_channel_ids.add(row["channel_id"].upper())

            writer.writerow(row)

            for discovered_platform, handles in contacts.items():
                if discovered_platform not in PLATFORM_SCRAPERS:
                    continue
                for raw in handles:
                    h = extract_handle(raw)
                    if not h:
                        continue
                    seen_key = (discovered_platform, h.lower())
                    if seen_key not in seen:
                        seen.add(seen_key)
                        stack.append((discovered_platform, h))
                        print(f"    -> Queued {discovered_platform}: {h}")

        except Exception as e:
            print(f"    Failed: {e}")

        if stack:
            time.sleep(DELAY)


def main():
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py channels.txt")
        sys.exit(1)

    seed_urls = load_urls(sys.argv[1])
    print(f"Loaded {len(seed_urls)} URLs from {sys.argv[1]}\n")

    fields = ["source_platform", "handle", "url"] + list(SOCIAL_PATTERNS.keys())

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()

        for i, seed_url in enumerate(seed_urls):
            print(f"[{i+1}/{len(seed_urls)}] {seed_url}")
            scrape_seed(seed_url, writer)
            f.flush()
            if i < len(seed_urls) - 1:
                print()

    print(f"\nDone. Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()