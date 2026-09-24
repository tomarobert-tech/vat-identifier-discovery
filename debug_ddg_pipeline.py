"""
Debug for the 0/25 result from ddg_pipeline.py - runs on just 5 companies, but
shows EVERY step: how many links the DDG search found, what status each page
gave when opened, and whether any VAT pattern was found on it.

This is the exact script that produced the "5 more companies... identical 202
status on every single query" finding described in README.md (Part 1,
source 1) - the evidence that DuckDuckGo was blocking automated requests,
not returning a genuine "nothing found" result.
"""

import json
import time
from ddg_pipeline import ddg_search_urls, scan_page_for_vat, VAT_NEAR_PATTERN, VAT_ANY_PATTERN, HEADERS
import requests

with open("sample_companies.json", "r", encoding="utf-8") as f:
    companies = json.load(f)[:5]

for comp in companies:
    name = comp["company_name"]
    print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")

    urls = ddg_search_urls(f'"{name}" VAT number')
    print(f"Links found by search: {len(urls)}")
    for u in urls:
        print(f"  - {u}")

    if not urls:
        print("  -> NO LINKS - the problem is the DDG search itself, not the pages after it")

    for url in urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            has_vat = bool(VAT_NEAR_PATTERN.search(res.text) or VAT_ANY_PATTERN.search(res.text))
            print(f"  fetch {url[:60]}... -> status {res.status_code}, "
                  f"length {len(res.text)}, VAT pattern found: {has_vat}")
        except Exception as e:
            print(f"  fetch {url[:60]}... -> ERROR: {e}")
        time.sleep(1)

    time.sleep(2)