"""
STEP 2 of the DuckDuckGo attempt - automates exactly what was done manually for
Ineo Nuclear: search "<company name> VAT number" on DuckDuckGo, open the first
few results, look for a VAT pattern on the page, verify with verify_helper.

This is the script that produced the 25-company test described in README.md
(Part 1, source 1): 0 candidates found, every search request returned an
unusual HTTP status (202) instead of a normal results page - a sign of
blocking, not of a genuine "no data" result (see debug_ddg_pipeline.py for the
follow-up that confirmed this). Not part of the final pipeline.

Run first with a small TEST_SIZE (20-30) to see the real success rate before
running on all 300 - it takes a while (each company = 1 search + up to 3 page
fetches, with delays).
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from verify_helper import verify_candidate

INPUT_SAMPLE = "sample_companies.json"
OUTPUT_RESULTS = "ddg_pipeline_results.json"
TEST_SIZE = 25          # start small
MAX_RESULTS_PER_COMPANY = 3   # how many search links to try per company
REQUEST_DELAY = 2       # seconds between requests - do not rush

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
}

VAT_NEAR_PATTERN = re.compile(r"VAT[^0-9]{0,25}GB\s?(\d{9})", re.IGNORECASE)
VAT_ANY_PATTERN = re.compile(r"\bGB\s?(\d{9})\b")


def ddg_search_urls(query: str) -> list:
    """Searches DuckDuckGo HTML and returns the organic result links."""
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"   [DEBUG] search error: {e}")
        return []

    if res.status_code != 200:
        print(f"   [DEBUG] search status: {res.status_code}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    links = []
    for a in soup.select("a.result__a")[:MAX_RESULTS_PER_COMPANY]:
        href = a.get("href")
        if href:
            links.append(href)
    return links


def scan_page_for_vat(url: str):
    """Opens a page and looks for a VAT pattern. Prefers the 'VAT ... GB123456789'
    pattern (safer), falls back to any GB+9digits only if nothing more specific
    is found."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
    except Exception:
        return None

    if res.status_code != 200:
        return None

    match = VAT_NEAR_PATTERN.search(res.text)
    if match:
        return match.group(1)

    match = VAT_ANY_PATTERN.search(res.text)
    if match:
        return match.group(1)

    return None


def run_pipeline():
    with open(INPUT_SAMPLE, "r", encoding="utf-8") as f:
        companies = json.load(f)[:TEST_SIZE]

    results = []
    coverage = 0
    matches = 0
    false_positives = 0

    for idx, comp in enumerate(companies, 1):
        name = comp["company_name"]
        print(f"\n[{idx}/{len(companies)}] {name}")

        urls = ddg_search_urls(f'"{name}" VAT number')
        time.sleep(REQUEST_DELAY)

        candidate = None
        source_url = None
        for url in urls:
            candidate = scan_page_for_vat(url)
            if candidate:
                source_url = url
                break
            time.sleep(REQUEST_DELAY)

        if not candidate:
            print("   no candidate found")
            results.append({**comp, "candidate_vat": None, "verdict": "NO_CANDIDATE"})
            continue

        coverage += 1
        r = verify_candidate(candidate, name, "duckduckgo-scan")
        r["source_url"] = source_url
        print(f"   candidate: {candidate} -> {r['verdict']} "
              f"(HMRC: '{r['hmrc_name']}', similarity: {r['name_similarity']})")

        if r["verdict"] == "MATCH":
            matches += 1
        elif r["verdict"] == "FALSE_POSITIVE_NAME_MISMATCH":
            false_positives += 1

        results.append({**comp, **r})

        # saved incrementally, so nothing is lost if something fails halfway
        with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    total = len(companies)
    print(f"\n{'=' * 50}")
    print(f"Total tested            : {total}")
    print(f"Coverage (candidate found): {coverage}/{total} ({100 * coverage / total:.1f}%)")
    print(f"Confirmed match          : {matches}")
    print(f"False positive           : {false_positives}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run_pipeline()