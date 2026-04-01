import re
from formats import SOCIAL_PATTERNS, PLATFORM_DOMAINS


def clean_handle(raw):
    h = re.sub(r"https?://", "", raw)
    h = re.sub(r"(?:www\.)?[^/]+\.[a-z]+/?", "", h, flags=re.I)
    h = h.strip("/").lstrip("@")
    h = re.sub(r"[.\u2026]+$", "", h)
    h = h.rstrip("_-")
    return h


def extract(html, exclude_platform=None):
    own_domains = PLATFORM_DOMAINS.get(exclude_platform, [])
    results = {}

    for key, pattern in SOCIAL_PATTERNS.items():
        if key == exclude_platform:
            results[key] = []
            continue

        matches = re.findall(pattern, html, re.I)
        matches = [m for m in matches if not any(d in m.lower() for d in own_domains)]

        if key == "emails":
            matches = [m for m in matches if not re.search(r"youtube|google|example", m, re.I)]
        elif key == "patreon":
            matches = [re.sub(r"https?://(?:www\.)?", "", m, flags=re.I) for m in matches]
        elif key == "bluesky":
            matches = [re.sub(r".*bsky\.app/profile/", "", m, flags=re.I) for m in matches]
            matches = [m for m in matches if m and "." in m]
        else:
            matches = [clean_handle(m) for m in matches]
            matches = [m for m in matches if m]

        # Deduplicate while preserving order
        seen = set()
        results[key] = [m for m in matches if not (m in seen or seen.add(m))]

    return results