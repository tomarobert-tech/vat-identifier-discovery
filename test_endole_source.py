"""
Tests the endole.co.uk source on a larger sample from sample_companies.json,
using the predictable URL pattern: /insight/company/{company_number}-{name_slug}.

This is the script that produced the "automated on a larger sample (40
companies), every single request came back with an HTTP 403 error" finding
in README.md (Part 1, source 6) - the Cloudflare block, confirmed here
before also being confirmed with cloudscraper in test_endole_cloudscraper.py.

Important - read before running on the full sample:
- Endole is a commercial product (sales intelligence / lead generation), not
  a primary government source. It has its own Terms of Use. For a PoC/
  challenge this is an acceptable grey area to explore, but it is NOT
  automatically an OK source to use in a commercial product without a
  licensing conversation - discussed explicitly in the Debate Topics section
  of README.md.
- A delay is added between requests (2s by default) out of courtesy - this
  is a single laptop, there is no need for speed, only for a correct result.
- Run FIRST on a small sample (e.g. 30-50), not all 300 at once - see
  SAMPLE_SIZE below.
"""

import json
import re
import time
import requests
from verify_helper import verify_candidate

INPUT_SAMPLE = "sample_companies.json"
OUTPUT_RESULTS = "endole_results.json"
SAMPLE_SIZE = 40  # start small, only increase if results look promising

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
}

VAT_PATTERN = re.compile(r"VAT Number\D{0,20}GB\s?(\d{9})", re.IGNORECASE)


def slugify(name: str) -> str:
    """Turns a company name into the slug format used by Endole in its URLs."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def fetch_endole_vat(company_number: str, company_name: str):
    """Tries to find a VAT Number on the company's Endole page.
    Returns (candidate_9_digits_or_None, status_code, response_length)."""
    url = f"https://open.endole.co.uk/insight/company/{company_number}-{slugify(company_name)}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    except Exception as e:
        print(f"   [DEBUG] Request error: {e}")
        return None, None, 0

    if res.status_code != 200:
        return None, res.status_code, len(res.text)

    match = VAT_PATTERN.search(res.text)
    candidate = match.group(1) if match else None
    return candidate, res.status_code, len(res.text)


def run_endole_test():
    with open(INPUT_SAMPLE, "r", encoding="utf-8") as f:
        companies = json.load(f)[:SAMPLE_SIZE]

    results = []
    coverage = 0
    matches = 0
    false_positives = 0

    print(f"Testing Endole.co.uk on {len(companies)} companies...\n")

    for idx, comp in enumerate(companies, 1):
        name = comp["company_name"]
        number = comp["company_number"]

        candidate, status, length = fetch_endole_vat(number, name)
        print(f"[{idx}/{len(companies)}] {name} -> "
              f"status {status}, candidate: {candidate}")

        if candidate:
            coverage += 1
            r = verify_candidate(candidate, name, "endole.co.uk")
            print(f"   verdict: {r['verdict']} (HMRC: '{r['hmrc_name']}', "
                  f"similarity: {r['name_similarity']})")
            if r["verdict"] == "MATCH":
                matches += 1
            elif r["verdict"] == "FALSE_POSITIVE_NAME_MISMATCH":
                false_positives += 1
            results.append({**comp, **r})
        else:
            results.append({**comp, "candidate_vat": None, "verdict": "NO_CANDIDATE"})

        time.sleep(2)  # polite delay - do not rush, do not load their server for nothing

    with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    total = len(companies)
    print(f"\n{'=' * 50}")
    print(f"Total tested            : {total}")
    print(f"Coverage (candidate found): {coverage}/{total} ({100 * coverage / total:.1f}%)")
    print(f"Confirmed match          : {matches}")
    print(f"False positive           : {false_positives}")
    print(f"{'=' * 50}")
    print(f"Results saved to '{OUTPUT_RESULTS}'")


if __name__ == "__main__":
    run_endole_test()