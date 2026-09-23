"""

This file has TWO roles, important to keep separate:

1. SHARED MODULE, ACTIVELY USED - is_valid_vat_checksum() and HEADERS are
   imported directly by pipeline_fixed.py and have stayed correct and
   unchanged since the start of the project.

2. HISTORICAL EVIDENCE - verify_hmrc_vat() and search_candidate_vat() are
   the ORIGINAL versions, with bugs found and fixed along the way (see
   README.md, "What I fixed along the way"). They are NOT used by the
   final pipeline anymore - pipeline_fixed.py has its own corrected
   versions (verify_hmrc_with_retry, search_candidates_structured).
   They are kept here unchanged, on purpose, as evidence of what happened.

Do NOT run this file directly (there is no __main__ block below, on
purpose) - use discovery.py and slow_verify.py instead, which use the
corrected versions from pipeline_fixed.py.
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


# ============================================================
# ACTIVELY USED - imported by pipeline_fixed.py
# ============================================================

def is_valid_vat_checksum(vat_digits: str) -> bool:
    """
    Validates the checksum of a UK VAT number (9 digits), modulus 97
    algorithm. A free, local filter applied BEFORE any request to
    HMRC - rejects clearly wrong candidates without spending a real
    request.

    The UK uses two variants of the formula (check_old for older VAT
    numbers, check_new with a +55 offset for ones issued after 2010) -
    a number is considered valid if it matches either one.
    """
    if len(vat_digits) != 9 or not vat_digits.isdigit():
        return False

    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(w * int(d) for w, d in zip(weights, vat_digits[:7]))
    check_digits = int(vat_digits[7:9])

    check_old = (97 - total % 97) % 97
    check_new = (97 - (total + 55) % 97) % 97

    return check_digits in (check_old, check_new)


# ============================================================
# HISTORICAL - original versions, with documented bugs.
# Kept unchanged as evidence, NOT used by the final pipeline.
# ============================================================

def verify_hmrc_vat(vat_number):
    """
    [OLD VERSION - replaced by verify_hmrc_with_retry() in pipeline_fixed.py]

    Verifies a VAT number through the full HMRC flow (session + CSRF +
    the 'target' field). Contains the bug described in the README: the
    check "valid uk vat number" in text_clean.lower() wrongly matches
    rejection pages too, because "invalid" literally contains "valid"
    as a substring. The corrected version checks the response's final
    URL (/known vs /unknown) instead of the page text.

    It also does not handle HTTP 429 (HMRC rate limiting) at all - any
    response other than 200-with-a-recognised-pattern silently falls
    through to return None, identical to an invalid VAT. See
    verify_hmrc_with_retry() for the corrected version, with explicit
    429 detection and retry.
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    start_url = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"

    try:
        res_init = session.get(start_url, timeout=10)
        if res_init.status_code != 200:
            return None

        soup_init = BeautifulSoup(res_init.text, "html.parser")
        csrf_input = soup_init.find("input", {"name": "csrfToken"})
        if not csrf_input:
            return None

        csrf_token = csrf_input.get("value")
        payload = {
            "csrfToken": csrf_token,
            "target": str(vat_number),
            "requester": "",
        }

        res_post = session.post(start_url, data=payload, timeout=10, allow_redirects=True)

        if res_post.status_code == 200:
            soup_res = BeautifulSoup(res_post.text, "html.parser")
            text_clean = " ".join(soup_res.get_text().split())

            match = re.search(
                r"Registered business name\s+(.*?)\s+Registered business address",
                text_clean, re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()

            # BUG: "invalid" contains the substring "valid" - see docstring
            if "valid uk vat number" in text_clean.lower():
                return "VALID_VAT_CONFIRMED"

    except Exception as e:
        print(f"   [ERROR] HMRC verification: {e}")

    return None


def search_candidate_vat(company_name):
    """
    [OLD VERSION - replaced by search_candidates_structured() in pipeline_fixed.py]

    Looks for a candidate VAT number on vat-lookup.co.uk, using a regex
    applied to the WHOLE page (not just the results table), taking the
    first candidate with a valid checksum.

    Documented bug (see README): when the results page contains more
    than one company (a search on a generic name - e.g. "Tesco"
    returned 24 different candidates on the same page), this function
    blindly takes the first one found, without checking whether the
    company name actually matches the search - a real, invisible false
    positive risk. The corrected version parses the actual table
    structure and picks the row whose name is the closest match.
    """
    url = "https://vat-lookup.co.uk/verify/search.php"
    payload = {"CompanyName": company_name}

    try:
        res = requests.post(url, data=payload, headers=HEADERS, timeout=8)

        if "Sorry" in res.text and "Nothing found" in res.text:
            return None

        if res.status_code == 200:
            matches = re.findall(r"GB\s?(\d{9})", res.text)
            for m in matches:
                if is_valid_vat_checksum(m):
                    return m  # first valid candidate found - see bug in docstring

    except Exception as e:
        print(f"   [ERROR] vat-lookup search: {e}")

    return None