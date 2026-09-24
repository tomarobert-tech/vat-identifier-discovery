"""
Why did HMRC reject 4 of the 5 candidates correctly found on vat-lookup.co.uk?
Checks the raw HMRC response directly for each one, to see whether it says
"not valid" explicitly, or whether the request itself is failing technically
(session/CSRF/parsing) - the same distinction applied everywhere else in this
project.

This is the script that produced the Umberslade/Tuoda Trading/Metier/Swiftsure
findings in Part 2 of README.md, and was reused the next day to confirm the
final 3 RATE_LIMITED candidates once HMRC's rate limit had cleared. "Rejected"
in the list name below reflects the initial suspicion at the time, not the
final result for every entry - two of these four turned out to be genuine
matches once actually checked (see README.md, Part 2, Results).
"""

import re
from bs4 import BeautifulSoup
import requests
from pipeline import HEADERS

REJECTED_CANDIDATES = [
    ("RAMONRA LTD", "314660128"),
    ("UMBERSLADE CORPORATE MANAGEMENT LIMITED DIRECTORS PENSION FUND", "559123631"),
    ("WPS LIVERPOOL LTD", "381634978"),
    ("SWIFTSURE DESIGN LIMITED", "144026249"),
]


def debug_hmrc_check(vat_number: str):
    session = requests.Session()
    session.headers.update(HEADERS)
    start_url = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"

    res_init = session.get(start_url, timeout=10)
    print(f"   Initial GET: status {res_init.status_code}")

    soup_init = BeautifulSoup(res_init.text, "html.parser")
    csrf_input = soup_init.find("input", {"name": "csrfToken"})
    if not csrf_input:
        print("   Could not find csrfToken on the initial page - possible structure change")
        return
    csrf_token = csrf_input.get("value")
    print(f"   csrf token found: {csrf_token[:15]}...")

    payload = {"csrfToken": csrf_token, "target": vat_number, "requester": ""}
    res_post = session.post(start_url, data=payload, timeout=10, allow_redirects=True)
    print(f"   POST: status {res_post.status_code}, final url: {res_post.url}")

    soup_res = BeautifulSoup(res_post.text, "html.parser")
    text_clean = " ".join(soup_res.get_text().split())

    # print a snippet of the text so we can see EXACTLY what HMRC says
    print(f"   Response text (first 400 characters):")
    print(f"   {text_clean[:400]}")
    print()


for name, vat in REJECTED_CANDIDATES:
    print(f"\n{'=' * 60}\n{name} - GB{vat}\n{'=' * 60}")
    debug_hmrc_check(vat)