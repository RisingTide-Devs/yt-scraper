import re
import sys
import time
import requests

DELAY = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def search_youtube(query, pages=1):
    handles = []
    params = {"search_query": query, "sp": "EgIQAg%3D%3D"}  # filter: channels only

    for page in range(pages):
        url = "https://www.youtube.com/results"
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        html = requests.utils.unquote(resp.text)

        # Extract @handles
        found = re.findall(r'"canonicalBaseUrl":"(/@[^"]+)"', html)
        handles.extend(found)

        # Also catch channel URLs without @
        found_legacy = re.findall(r'"canonicalBaseUrl":"(/(?:c|user)/[^"]+)"', html)
        handles.extend(found_legacy)

        # Get continuation token for next page
        token = re.search(r'"continuationCommand":\{"token":"([^"]+)"', html)
        if not token or page == pages - 1:
            break

        time.sleep(DELAY)
        params = {"ctoken": token.group(1), "continuation": token.group(1)}

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for h in handles:
        if h not in seen:
            seen.add(h)
            unique.append(h)

    return unique


def main():
    if len(sys.argv) < 2:
        print("Usage: python youtube_search.py \"keyword\" [pages]")
        print("  pages: number of result pages to scrape (default: 1)")
        sys.exit(1)

    query = sys.argv[1]
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    print(f"Searching YouTube for: {query!r} ({pages} page(s))\n")
    handles = search_youtube(query, pages)

    if not handles:
        print("No channels found.")
        sys.exit(0)

    print(f"Found {len(handles)} channels:\n")
    for h in handles:
        print(h.lstrip("/"))

    output_file = "channels.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for h in handles:
            f.write(h.lstrip("/") + "\n")

    print(f"\nSaved to {output_file}")


if __name__ == "__main__":
    main()