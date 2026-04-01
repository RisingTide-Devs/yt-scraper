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

CHANNEL_ID_LENGTH = 24  # UC + 22 chars


def load_channels(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def normalize_channel(raw):
    """
    Accept any YouTube handle/URL format and return (handle, url).
    Handles: @handle, handle, channel/UCxxx, full URLs.
    Returns (None, None) if the channel ID is invalid.
    """
    # Strip full URL down to just the path portion
    h = re.sub(r"https?://(?:www\.)?youtube\.com/", "", raw, flags=re.I)
    h = h.strip("/")

    # channel/UC... format
    if re.match(r"channel/", h, re.I):
        channel_id = h.split("/")[-1]
        # Restore UC prefix if lowercased
        if not channel_id.startswith("UC"):
            channel_id = "UC" + channel_id[2:]
        # Validate full channel ID length
        if len(channel_id) != CHANNEL_ID_LENGTH:
            return None, None
        url = f"https://www.youtube.com/channel/{channel_id}/about"
        return f"channel/{channel_id}", url

    # @handle or bare handle
    handle = h.lstrip("@")
    url = f"https://www.youtube.com/@{handle}/about"
    return handle, url


def scrape(raw):
    handle, url = normalize_channel(raw)
    if not handle:
        raise ValueError(f"Invalid or truncated YouTube channel identifier: {raw!r}")

    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    html = requests.utils.unquote(resp.text)

    # Extract canonical channel ID for dedup in orchestrator
    channel_id_match = re.search(r'"channelId"\s*:\s*"(UC[^"]+)"', html)
    channel_id = channel_id_match.group(1) if channel_id_match else None

    contacts = extract(html, exclude_platform="youtube")

    row = {"handle": handle, "url": url}
    if channel_id:
        row["channel_id"] = channel_id
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
            rows.append({"handle": channel, "url": "", "error": str(e)})
        if i < len(channels) - 1:
            time.sleep(DELAY)

    fields = ["handle", "url"] + list(SOCIAL_PATTERNS.keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()