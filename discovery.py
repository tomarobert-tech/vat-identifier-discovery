"""
Runs ONLY the search step (vat-lookup.co.uk), without touching HMRC at all.
Gives a safe, raw coverage number, with zero rate-limit risk, which can be
reported separately from the candidates that are fully verified against HMRC
in slow_verify.py.
"""

import json
import time
from pipeline_fixed import search_candidates_structured

INPUT_SAMPLE = "sample_companies.json"
OUTPUT_RESULTS = "discovery_only_results.json"


def run_discovery_only(sample_size=300):
    with open(INPUT_SAMPLE, "r", encoding="utf-8") as f:
        companies = json.load(f)[:sample_size]

    results = []
    found = 0

    for idx, comp in enumerate(companies, 1):
        name = comp["company_name"]
        candidates = search_candidates_structured(name)

        if candidates:
            best = max(candidates, key=lambda c: c[2])
            row_name, candidate_vat, sim = best
            found += 1
            print(f"[{idx}/{len(companies)}] {name} -> candidate: '{row_name}' "
                  f"(GB{candidate_vat}), similarity {sim:.2f}")
            results.append({
                "company_name": name,
                "company_number": comp["company_number"],
                "matched_row_name": row_name,
                "candidate_vat": candidate_vat,
                "name_similarity": round(sim, 2),
                "hmrc_verified": False,  # to be completed separately, no rush
            })
        else:
            results.append({
                "company_name": name,
                "company_number": comp["company_number"],
                "candidate_vat": None,
            })

        with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        time.sleep(1)  # just politeness towards vat-lookup.co.uk, no HMRC risk here

    print(f"\n{'=' * 50}")
    print(f"Total processed        : {len(companies)}")
    print(f"Candidates found (not yet HMRC-verified): {found}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run_discovery_only(sample_size=300)