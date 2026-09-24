"""
Isolated debug for the vat-lookup.co.uk source.
Run THIS locally (not in a sandbox) - it saves the raw response to disk so
you can inspect exactly what comes back, not just what the code says about it.

This is the script that produced the debug_response_1_*.html and
debug_response_2_*.html files referenced in README.md (Part 1, source 5, and
Setup): British Telecommunications as the positive control (VAT found
correctly), and Edelweiss Cheddar Limited showing the site's own "not
discovered yet" message - the first confirmed evidence that vat-lookup.co.uk
was working correctly but simply had no data for a small company at the time.
"""

import requests
from pipeline import is_valid_vat_checksum, HEADERS

URL = "https://vat-lookup.co.uk/verify/search.php"

# A large company, already manually confirmed to have an easily findable VAT,
# plus 2-3 random companies from the 300-company sample (copied from
# sample_companies.json).
TEST_CASES = [
    "British Telecommunications",   # positive control - should work if the source works at all
    "EDELWEISS (CHEDDAR) LIMITED",  # replace with 2-3 real names from sample_companies.json
]

BLOCKING_SIGNALS = [
    "captcha", "cloudflare", "access denied", "blocked",
    "just a moment", "unusual traffic", "rate limit",
]


def debug_one(company_name: str, idx: int):
    print(f"\n{'=' * 60}\nTesting: {company_name}\n{'=' * 60}")

    # 1. Request without custom headers - see if the User-Agent matters
    for label, headers in [("WITH HEADERS", HEADERS), ("WITHOUT HEADERS", {})]:
        try:
            res = requests.post(
                URL, data={"CompanyName": company_name},
                headers=headers, timeout=10, allow_redirects=True,
            )
        except Exception as e:
            print(f"  [{label}] request ERROR: {e}")
            continue

        body_lower = res.text.lower()
        signals = [s for s in BLOCKING_SIGNALS if s in body_lower]
        gb_matches = __import__("re").findall(r"GB\s?(\d{9})", res.text)
        valid_checksums = [m for m in gb_matches if is_valid_vat_checksum(m)]

        print(f"  [{label}]")
        print(f"    status_code       : {res.status_code}")
        print(f"    final url         : {res.url}")
        print(f"    content-type      : {res.headers.get('content-type')}")
        print(f"    response length   : {len(res.text)} characters")
        print(f"    blocking signals  : {signals or 'none detected'}")
        print(f"    contains 'Sorry'  : {'Sorry' in res.text}")
        print(f"    GB+9digits found  : {gb_matches}")
        print(f"    valid checksum    : {valid_checksums}")

        # save the raw response so you can look directly inside it
        fname = f"debug_response_{idx}_{label.replace(' ', '_')}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(res.text)
        print(f"    saved to          : {fname}  <- open it in a browser or editor")


if __name__ == "__main__":
    for i, name in enumerate(TEST_CASES, 1):
        debug_one(name, i)

    print(
        "\n\nHow to read the result:\n"
        "- If British Telecommunications returns valid GB+9digits, but the random "
        "company doesn't -> the source genuinely does not cover small companies "
        "(a real dead end, document it with numbers).\n"
        "- If NEITHER returns anything, but the response length is small/suspicious "
        "or blocking signals appear -> you are blocked, this is not a real result yet. "
        "Try from a different network (a different IP), with a longer delay between "
        "requests, or check manually in a browser whether the form is still the same.\n"
        "- Open the saved .html files - if they look like a generic error page or a "
        "blank screen, that is a clear sign of blocking, not of 'no data'.\n"
    )