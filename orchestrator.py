"""
orchestrator.py — scrape a list of YouTube handles, then follow all discovered social links.

Usage:
    python orchestrator.py channels.txt

Adding a new platform:
    1. Create scrapers/<platform>.py with a scrape(handle) -> (handle, url, contacts) function
    2. Import it below and add it to the SCRAPERS dict
"""

import csv
import re
import sys
import time

from formats import SOCIAL_PATTERNS, ABOUT_URLS
import scrapers.ytScraper as youtube
import scrapers.twitterScraper as twitter_x
import scrapers.igScraper as instagram
import scrapers.tiktokScraper as tiktok
import scrapers.fbScraper as facebook
import scrapers.ttvScraper as twitch

OUTPUT_FILE = "contacts.csv"
DELAY = 1.5

# To add a new platform: import its module above and add it here
SCRAPERS = {
    "twitter_x": twitter_x,
    "instagram":  instagram,
    "tiktok":     tiktok,
    "facebook":   facebook,
    "twitch":     twitch,
}


def load_channels(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def scrape_channel(channel):
    rows = []

    # --- Step 1: YouTube (returns a flat row dict, as per original ytScraper.py) ---
    try:
        yt_row = youtube.scrape(channel)
    except Exception as e:
        print(f"  YouTube scrape failed: {e}")
        return rows

    yt_row["source_platform"] = "youtube"
    rows.append(yt_row)

    # --- Step 2: Follow each discovered platform ---
    for platform, scraper in SCRAPERS.items():
        if platform not in ABOUT_URLS:
            continue
        handles = [h.strip() for h in yt_row.get(platform, "").split(",") if h.strip()]
        if not handles:
            continue

        seen_handles = set()
        for handle in handles:
            handle = re.sub(r"https?://", "", handle)
            handle = re.sub(r"(?:www\.)?[^/]+\.com/?", "", handle, flags=re.I)
            handle = handle.strip("/").lstrip("@").lower()
            if not handle or handle in seen_handles:
                continue
            seen_handles.add(handle)

            print(f"  -> Scraping {platform}: {handle}")
            try:
                time.sleep(DELAY)
                p_handle, p_url, p_contacts = scraper.scrape(handle)
                p_row = {"source_platform": platform, "handle": p_handle, "url": p_url}
                for key, found in p_contacts.items():
                    p_row[key] = ", ".join(found)
                rows.append(p_row)
            except Exception as e:
                print(f"     Failed: {e}")
                rows.append({"source_platform": platform, "handle": handle, "url": "", "error": str(e)})

        time.sleep(DELAY)

    return rows


def main():
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py channels.txt")
        sys.exit(1)

    channels = load_channels(sys.argv[1])
    print(f"Loaded {len(channels)} channels from {sys.argv[1]}\n")

    all_rows = []

    for i, channel in enumerate(channels):
        print(f"[{i+1}/{len(channels)}] Scraping YouTube: {channel}")
        rows = scrape_channel(channel)
        all_rows.extend(rows)
        if i < len(channels) - 1:
            time.sleep(DELAY)

    fields = ["source_platform", "channel", "url"] + list(SOCIAL_PATTERNS.keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()