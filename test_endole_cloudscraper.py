"""
STEP 1 - tries to get past Endole's Cloudflare protection using cloudscraper.
Run this FIRST, on just a few companies, to quickly see whether it is worth
continuing. If it still gives 403/challenge after 10-15 minutes, abandon this
and move to Step 2 (DuckDuckGo).

This is the script behind the "also tried cloudscraper... and still got
blocked every time" finding in README.md (Part 1, source 6) - confirming the
Cloudflare block was not just a plain-`requests` problem.

pip install cloudscraper
"""

import time
import cloudscraper
from test_endole_source import slugify, VAT_PATTERN
from verify_helper import verify_candidate

scraper = cloudscraper.create_scraper()

# Test first on just these 3 - one where we KNOW a VAT exists (control), two from the sample
TEST_CASES = [
    ("09905931", "Ineo Nuclear UK Ltd"),   # positive control - known VAT: GB365998427
    ("04169780", "Globe UK Holding Ltd"),
    ("13547774", "Ozero Tech Ltd"),
]

for number, name in TEST_CASES:
    url = f"https://open.endole.co.uk/insight/company/{number}-{slugify(name)}"
    try:
        res = scraper.get(url, timeout=15)
    except Exception as e:
        print(f"{name}: ERROR - {e}")
        continue

    print(f"\n{name}")
    print(f"  status: {res.status_code}")
    print(f"  length: {len(res.text)}")

    if res.status_code == 200:
        match = VAT_PATTERN.search(res.text)
        if match:
            candidate = match.group(1)
            r = verify_candidate(candidate, name, "endole-cloudscraper")
            print(f"  CANDIDATE FOUND: {candidate} -> {r['verdict']}")
        else:
            print("  200 OK, but no VAT Number found on the page")
    else:
        print(f"  Still blocked (status {res.status_code}) - cloudscraper did not solve it")

    time.sleep(2)