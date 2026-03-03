import re
import csv
import time
import requests

CHANNELS = [
    "@MrBeast",
    "@mkbhd",
    "@veritasium",
    "@kurzgesagt",
]

OUTPUT_FILE = "youtube_contacts.csv"
DELAY = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

SOCIAL_PATTERNS = {
    "emails":    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "twitter_x": r"(?:twitter\.com|x\.com)/[A-Za-z0-9_]+",
    "instagram": r"instagram\.com/[A-Za-z0-9_.]+",
    "tiktok":    r"tiktok\.com/@?[A-Za-z0-9_.]+",
    "facebook":  r"facebook\.com/[A-Za-z0-9_.]+",
    "linkedin":  r"linkedin\.com/(?:in|company)/[A-Za-z0-9_\-]+",
    "twitch":    r"twitch\.tv/[A-Za-z0-9_]+",
    "discord":   r"discord\.(?:gg|com/invite)/[A-Za-z0-9_\-]+",
    "patreon":   r"patreon\.com/[A-Za-z0-9_]+",
}


def scrape(channel):
    handle = channel if channel.startswith("@") else f"@{channel}"
    url = f"https://www.youtube.com/{handle}/about"

    resp = requests.get(url, headers=HEADERS, timeout=10)
    # YouTube encodes external links as URL-encoded query params — decode them
    html = requests.utils.unquote(resp.text)

    row = {"channel": channel, "url": url}
    for key, pattern in SOCIAL_PATTERNS.items():
        matches = re.findall(pattern, html, re.I)
        if key == "emails":
            matches = [m for m in matches if not re.search(r"youtube|google", m, re.I)]
        row[key] = ", ".join(sorted(set(matches)))

    return row


def main():
    rows = []
    for i, channel in enumerate(CHANNELS):
        print(f"Scraping {channel}...")
        try:
            rows.append(scrape(channel))
        except Exception as e:
            print(f"  Failed: {e}")
            rows.append({"channel": channel, "error": str(e)})
        if i < len(CHANNELS) - 1:
            time.sleep(DELAY)

    fields = ["channel", "url", "emails"] + [k for k in SOCIAL_PATTERNS if k != "emails"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
