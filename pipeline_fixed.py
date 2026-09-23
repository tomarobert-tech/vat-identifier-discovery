"""
Corrected version of the pipeline, with two fixes compared to the original
pipeline.py:

1. Candidate extraction: parses the actual results table on vat-lookup.co.uk
   (company name + VAT per row) and picks the row whose name is the closest
   match to the company being searched - not just the first GB+9-digit
   pattern found anywhere on the page.

2. HMRC verification with retry: explicitly detects HTTP 429 ("Too Many
   Requests") from HMRC and retries with backoff, instead of silently
   treating a rate limit as an "invalid VAT". Without this, results vary
   between runs for reasons that have nothing to do with the real data.
"""

import re
import time
import json
from bs4 import BeautifulSoup
import requests
from pipeline import is_valid_vat_checksum, HEADERS
from verify_helper import name_similarity

INPUT_SAMPLE = "sample_companies.json"
OUTPUT_RESULTS = "pipeline_results_fixed.json"

HMRC_START_URL = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"


def search_candidates_structured(company_name: str):
    """Returns the list of ALL candidates found in the results table,
    as (row_name, vat_digits, name_similarity)."""
    url = "https://vat-lookup.co.uk/verify/search.php"
    payload = {"CompanyName": company_name}

    try:
        res = requests.post(url, data=payload, headers=HEADERS, timeout=8)
    except Exception as e:
        print(f"   [DEBUG] Search request error: {e}")
        return []

    if "Sorry" in res.text and "Nothing found" in res.text:
        return []
    if res.status_code != 200:
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    candidates = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue  # skips the header row

        row_company_name = cells[0].get_text(strip=True)
        vat_link = row.find("a", href=re.compile(r"VATNumber"))
        if not vat_link:
            continue

        m = re.search(r"GB(\d{9})", vat_link.get_text())
        if not m:
            continue

        digits = m.group(1)
        if not is_valid_vat_checksum(digits):
            continue

        sim = name_similarity(row_company_name, company_name)
        candidates.append((row_company_name, digits, sim))

    return candidates


def verify_hmrc_with_retry(vat_number: str, max_retries: int = 3, backoff_seconds: int = 8):
    """Same as verify_hmrc_vat in pipeline.py, but explicitly detects 429
    (rate limit) and retries instead of silently returning None.

    Returns (result, status):
      result - the HMRC name if it worked, otherwise None
      status - one of "OK", "REJECTED" (HMRC explicitly says it's not valid),
                "RATE_LIMITED" (every attempt hit 429), "ERROR" (something else)
    """
    for attempt in range(1, max_retries + 1):
        session = requests.Session()
        session.headers.update(HEADERS)

        try:
            res_init = session.get(HMRC_START_URL, timeout=10)
            if res_init.status_code != 200:
                return None, "ERROR"

            soup_init = BeautifulSoup(res_init.text, "html.parser")
            csrf_input = soup_init.find("input", {"name": "csrfToken"})
            if not csrf_input:
                return None, "ERROR"
            csrf_token = csrf_input.get("value")

            payload = {"csrfToken": csrf_token, "target": str(vat_number), "requester": ""}
            res_post = session.post(HMRC_START_URL, data=payload, timeout=10, allow_redirects=True)

            if res_post.status_code == 429:
                print(f"   [DEBUG] HMRC 429 (attempt {attempt}/{max_retries}) - waiting {backoff_seconds}s")
                time.sleep(backoff_seconds)
                continue  # try again

            if res_post.status_code == 200:
                soup_res = BeautifulSoup(res_post.text, "html.parser")
                text_clean = " ".join(soup_res.get_text().split())

                # use the final URL - more reliable than searching the text,
                # since "invalid" literally contains the substring "valid",
                # so a naive text search confuses rejections with confirmations
                if res_post.url.rstrip("/").endswith("/known"):
                    match = re.search(
                        r"Registered business name\s+(.*?)\s+Registered business address",
                        text_clean, re.IGNORECASE,
                    )
                    if match:
                        return match.group(1).strip(), "OK"
                    return "VALID_VAT_CONFIRMED", "OK"

                if res_post.url.rstrip("/").endswith("/unknown"):
                    return None, "REJECTED"

                # unexpected URL - do not assume anything, treat as an error to check manually
                return None, "ERROR"

            return None, "ERROR"

        except Exception as e:
            print(f"   [DEBUG] HMRC verification error: {e}")
            return None, "ERROR"

    return None, "RATE_LIMITED"


def diagnose_and_fix(sample_size=300, verbose_first_n=15):
    with open(INPUT_SAMPLE, "r", encoding="utf-8") as f:
        companies = json.load(f)[:sample_size]

    # RESUME: if results are already saved, skip companies already resolved
    # (any status other than RATE_LIMITED) - do not redo them.
    try:
        with open(OUTPUT_RESULTS, "r", encoding="utf-8") as f:
            results = json.load(f)
        done_numbers = {r["company_number"] for r in results if r["status"] != "RATE_LIMITED"}
        results = [r for r in results if r["status"] != "RATE_LIMITED"]
        print(f"Resuming: {len(done_numbers)} companies already resolved, skipping them.\n")
    except FileNotFoundError:
        results = []
        done_numbers = set()

    matches = sum(1 for r in results if r["status"] == "MATCH_CONFIRMED")
    false_candidates = sum(1 for r in results if r["status"] == "FALSE_CANDIDATE")
    no_candidates = sum(1 for r in results if r["status"] == "NO_CANDIDATE")
    rate_limited = 0

    for idx, comp in enumerate(companies, 1):
        if comp["company_number"] in done_numbers:
            continue

        name = comp["company_name"]
        candidates = search_candidates_structured(name)

        if idx <= verbose_first_n:
            print(f"\n[{idx}] {name}")
            print(f"   rows found in table: {len(candidates)}")
            for row_name, digits, sim in candidates:
                print(f"     - '{row_name}' (GB{digits}), similarity: {sim:.2f}")

        status = "NO_CANDIDATE"
        candidate_vat = None
        hmrc_name = None

        if candidates:
            best = max(candidates, key=lambda c: c[2])
            row_name, candidate_vat, sim = best

            # a single attempt here - if you are already rate-limited, more
            # quick attempts do not help; recovery happens separately, with slow_verify.py
            hmrc_name, hmrc_status = verify_hmrc_with_retry(candidate_vat, max_retries=1)

            if idx <= verbose_first_n:
                print(f"   -> candidate picked: '{row_name}' (GB{candidate_vat}), "
                      f"similarity {sim:.2f}, HMRC status: {hmrc_status}")

            if hmrc_status == "OK":
                # final check: does the name HMRC confirmed actually match
                # the company being searched for, not just the row picked from
                # the table? A VAT number can be valid and active, but belong
                # to a different entity (e.g. the company's own pension fund,
                # not the company itself).
                final_sim = name_similarity(hmrc_name, name)
                if final_sim >= 0.85:
                    status = "MATCH_CONFIRMED"
                    matches += 1
                else:
                    status = "FALSE_CANDIDATE"
                    false_candidates += 1
                    if idx <= verbose_first_n:
                        print(f"   [WARNING] HMRC confirms a valid VAT, but the name "
                              f"('{hmrc_name}') does not match the company being "
                              f"searched for ('{name}') closely enough - final "
                              f"similarity {final_sim:.2f}. Marked FALSE_CANDIDATE "
                              f"(wrong entity).")
            elif hmrc_status == "RATE_LIMITED":
                status = "RATE_LIMITED"
                rate_limited += 1
            else:
                status = "FALSE_CANDIDATE"
                false_candidates += 1

        else:
            no_candidates += 1

        results.append({
            "company_name": name,
            "company_number": comp["company_number"],
            "candidate_vat": candidate_vat,
            "hmrc_registered_name": hmrc_name,
            "status": status,
        })

        with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        time.sleep(2)  # a more generous delay - HMRC is a real government service

    print(f"\n{'=' * 50}")
    print(f"Total processed      : {len(companies)}")
    print(f"MATCH_CONFIRMED      : {matches}")
    print(f"FALSE_CANDIDATE      : {false_candidates}")
    print(f"RATE_LIMITED (retry) : {rate_limited}")
    print(f"NO_CANDIDATE         : {no_candidates}")
    print(f"{'=' * 50}")
    if rate_limited:
        print(f"{rate_limited} companies are still RATE_LIMITED - run again on "
              f"just those (not the whole sample) to clear them.")


if __name__ == "__main__":
    diagnose_and_fix(sample_size=300, verbose_first_n=20)