"""
Test framework for two sources: EORI and legal website disclosure
(Provision of Services Regulations 2009) - the framework behind the 0/8
results for both, described in README.md (Part 1, sources 3 and 4).

How to use this file:
1. Manually search (web, trade aggregators, company websites) for candidates
   for 8-10 companies from sample_companies.json.
2. Fill in the lists below with what you found (or None if you found
   nothing - that is a valid result, do not leave it out).
3. Run the script - it does the full verification (checksum + HMRC + name
   comparison) and gives you a summary you can copy straight into the
   research log.
"""

from verify_helper import verify_candidate

# --- SOURCE A: EORI ---
# Official format confirmed (gov.uk/guidance/economic-operators-registration-and-identification-eori):
# EORI = "GB" + (9-digit VAT) + "000" for VAT-registered companies.
# Enter only the 9 digits in the middle here (no GB, no trailing 000).

EORI_TEST_CASES = [
    # (exact_company_name_from_sample, vat_digits_from_eori_or_None)
]

# --- SOURCE B: VAT published on the company's own website ---
# Search the company's website, then in the footer / Terms / Legal / About
# pages, for a pattern like "VAT No: GB123456789" or "VAT Reg. No 123456789".
# Enter only the 9 digits here.

WEBSITE_TEST_CASES = [
    # (exact_company_name_from_sample, vat_digits_found_on_site_or_None)
]


def run_source_test(cases, source_name):
    print(f"\n{'=' * 60}\nSOURCE: {source_name}\n{'=' * 60}")
    results = []

    for company_name, candidate in cases:
        if not candidate:
            print(f"{company_name}: NO CANDIDATE FOUND")
            results.append({"verdict": "NO_CANDIDATE"})
            continue

        r = verify_candidate(candidate, company_name, source_name)
        print(
            f"{company_name}: {r['verdict']} "
            f"(HMRC: '{r['hmrc_name']}', name similarity: {r['name_similarity']})"
        )
        results.append(r)

    total = len(results)
    no_cand = sum(1 for r in results if r["verdict"] == "NO_CANDIDATE")
    matches = sum(1 for r in results if r["verdict"] == "MATCH")
    false_pos = sum(1 for r in results if r["verdict"] == "FALSE_POSITIVE_NAME_MISMATCH")
    hmrc_rejected = sum(1 for r in results if r["verdict"] == "HMRC_REJECTED")

    print(f"\n--- {source_name} summary ---")
    print(f"Total tested                            : {total}")
    print(f"Coverage (candidate found)              : {total - no_cand}/{total}")
    print(f"Confirmed match (name matches)           : {matches}")
    print(f"False positive (valid VAT, other company): {false_pos}")
    print(f"Rejected by HMRC                         : {hmrc_rejected}")

    return results


if __name__ == "__main__":
    run_source_test(EORI_TEST_CASES, "EORI")
    run_source_test(WEBSITE_TEST_CASES, "Website VAT disclosure")