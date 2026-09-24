"""
One of the earliest exploratory scripts: tries the original (now historical)
search_candidate_vat and verify_hmrc_vat functions from pipeline.py on 5
large, well-known companies, to sanity-check the whole discover-then-verify
idea before scaling it up to the full 300-company sample.
"""

from pipeline import search_candidate_vat, verify_hmrc_vat

# Large companies, where manual checking (Google) already confirmed the VAT is findable
test_companies = [
    "British Telecommunications",
    "British Airways",
    "Vodafone",
    "Tesco",
    "BP",
]

for name in test_companies:
    print(f"\n=== Testing: {name} ===")
    candidate = search_candidate_vat(name)

    if candidate:
        print(f"   Candidate found: GB{candidate}")
        hmrc_name = verify_hmrc_vat(candidate)
        if hmrc_name:
            print(f"   Confirmed by HMRC: {hmrc_name}")
        else:
            print("   Rejected by HMRC")
    else:
        print("   No candidate found")