"""
Debug pentru 0/25 - ruleaza pe doar 5 companii, dar iti arata FIECARE pas:
cate linkuri a gasit cautarea DDG, ce status a avut fiecare pagina cand a
incercat sa o deschida, si daca a gasit vreun pattern VAT pe ea.
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
    print(f"Linkuri gasite de cautare: {len(urls)}")
    for u in urls:
        print(f"  - {u}")

    if not urls:
        print("  -> NICIUN LINK - problema e la cautarea DDG insasi, nu la paginile ulterioare")

    for url in urls:
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            has_vat = bool(VAT_NEAR_PATTERN.search(res.text) or VAT_ANY_PATTERN.search(res.text))
            print(f"  fetch {url[:60]}... -> status {res.status_code}, "
                  f"lungime {len(res.text)}, pattern VAT gasit: {has_vat}")
        except Exception as e:
            print(f"  fetch {url[:60]}... -> EROARE: {e}")
        time.sleep(1)

    time.sleep(2)