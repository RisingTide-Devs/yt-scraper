import re
import csv
import sys
import time
import requests
from formats import SOCIAL_PATTERNS, ABOUT_URLS, PLATFORM_DOMAINS

OUTPUT_FILE = "social_contacts.csv"
DELAY = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}



def load_channels(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return requests.utils.unquote(resp.text)


def clean_handle(match):
    # Strip protocol, www, and domain — keep only the path after the domain
    match = re.sub(r"https?://(?:www\.)?[^/]+/", "", match)
    match = re.sub(r"^(?:www\.)?[^/]+/", "", match)
    return match.strip("/").lstrip("@")

def extract_socials(html, exclude_platform=None):
    own_domains = PLATFORM_DOMAINS.get(exclude_platform, [])
    results = {}
    for key, pattern in SOCIAL_PATTERNS.items():
        if key == exclude_platform:
            results[key] = []
            continue
        matches = re.findall(pattern, html, re.I)
        matches = [m for m in matches if not any(d in m.lower() for d in own_domains)]
        if key == "emails":
            matches = [m for m in matches if not re.search(r"youtube|google", m, re.I)]
        else:
            matches = [clean_handle(m) for m in matches]
        results[key] = sorted(set(matches))
    return results


def scrape_youtube(handle):
    handle = handle if handle.startswith("@") else f"@{handle}"
    url = f"https://www.youtube.com/{handle}/about"
    html = fetch(url)
    socials = extract_socials(html, exclude_platform="youtube")
    return handle, url, socials



def scrape_platform(platform, handle):
    handle = clean_handle(handle)
    url = ABOUT_URLS[platform].format(handle=handle)
    html = fetch(url)
    socials = extract_socials(html, exclude_platform=platform)
    return url, socials


def main():
    if len(sys.argv) < 2:
        print("Usage: python social_scraper.py channels.txt")
        sys.exit(1)

    channels = load_channels(sys.argv[1])
    print(f"Loaded {len(channels)} YouTube channels\n")

    all_rows = []

    for i, channel in enumerate(channels):
        print(f"[{i+1}/{len(channels)}] Scraping YouTube: {channel}")
        try:
            handle, yt_url, yt_socials = scrape_youtube(channel)
        except Exception as e:
            print(f"  Failed: {e}")
            all_rows.append({"source_platform": "youtube", "handle": channel, "url": "", "error": str(e)})
            time.sleep(DELAY)
            continue

        # Write the YouTube row
        yt_row = {"source_platform": "youtube", "handle": handle, "url": yt_url}
        for key, matches in yt_socials.items():
            yt_row[key] = ", ".join(matches)
        all_rows.append(yt_row)

        # Now scrape each social found on the YouTube page
        for platform, matches in yt_socials.items():
            if platform not in ABOUT_URLS or not matches:
                continue
            seen_handles = set()
            for match in matches:
                handle_key = clean_handle(match)
                if handle_key in seen_handles:
                    continue
                seen_handles.add(handle_key)
                print(f"  -> Scraping {platform}: {handle_key}")
                try:
                    p_url, p_socials = scrape_platform(platform, match)
                    p_row = {"source_platform": platform, "handle": handle_key, "url": p_url}
                    for key, found in p_socials.items():
                        p_row[key] = ", ".join(found)
                    all_rows.append(p_row)
                except Exception as e:
                    print(f"     Failed: {e}")
                    all_rows.append({"source_platform": platform, "handle": handle_key, "url": "", "error": str(e)})
                time.sleep(DELAY)

        time.sleep(DELAY)

    fields = ["source_platform", "handle", "url"] + list(SOCIAL_PATTERNS.keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()