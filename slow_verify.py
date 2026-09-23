"""
"Slow and patient" verification of the candidates already found (from
discovery_only_results.json), with long pauses between requests, so HMRC's
rate limit does not get triggered again. Start it, let it run in the
background, check progress from time to time - safe to interrupt and
resume, saves incrementally.
"""

import json
import time
from pipeline_fixed import verify_hmrc_with_retry
from verify_helper import name_similarity

DISCOVERY_FILE = "discovery_only_results.json"
OUTPUT_FILE = "final_verified_results.json"
DELAY_SECONDS = 50  # intentionally generous - do not rush

# companies already verified manually, skip re-checking them
ALREADY_VERIFIED = {
    "RAMONRA LTD": ("MATCH_CONFIRMED", "RAMONRA LTD"),
    "WPS LIVERPOOL LTD": ("MATCH_CONFIRMED", "WPS LIVERPOOL LTD"),
    "SWIFTSURE DESIGN LIMITED": ("FALSE_CANDIDATE", None),  # HMRC: invalid
    "UMBERSLADE CORPORATE MANAGEMENT LIMITED": (
        "FALSE_CANDIDATE",
        "UMBERSLADE CORPORATE MANAGEMENT LIMITED DIRECTORS PENSION FUND",
    ),  # wrong entity
    "DEVOPTIMIZE LTD": ("MATCH_CONFIRMED", "DEVOPTIMIZE LTD"),
    "MASCO CONSTRUCTION LTD": ("FALSE_CANDIDATE", None),  # HMRC: invalid
    "EVER GEEEN LIMITED": ("FALSE_CANDIDATE", None),  # HMRC: invalid
}


def load_or_init():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def run():
    with open(DISCOVERY_FILE, "r", encoding="utf-8") as f:
        discovered = [d for d in json.load(f) if d.get("candidate_vat")]

    results = load_or_init()
    # RESUME FIX: RATE_LIMITED entries are not actually "done" - drop them so
    # they get retried (or picked up from ALREADY_VERIFIED) instead of being
    # skipped forever just because they are already present in the file.
    results = [r for r in results if r["status"] != "RATE_LIMITED"]
    done_numbers = {r["company_number"] for r in results}

    for item in discovered:
        name = item["company_name"]
        number = item["company_number"]
        vat = item["candidate_vat"]

        if number in done_numbers:
            continue

        if name in ALREADY_VERIFIED:
            status, hmrc_name = ALREADY_VERIFIED[name]
            print(f"{name}: already verified manually -> {status}")
            results.append({"company_name": name, "company_number": number,
                             "candidate_vat": vat, "hmrc_registered_name": hmrc_name,
                             "status": status})
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
            continue

        hmrc_name, hmrc_status = verify_hmrc_with_retry(vat, max_retries=1)

        if hmrc_status == "OK":
            sim = name_similarity(hmrc_name, name)
            status = "MATCH_CONFIRMED" if sim >= 0.85 else "FALSE_CANDIDATE"
        elif hmrc_status == "RATE_LIMITED":
            status = "RATE_LIMITED"
        else:
            status = "FALSE_CANDIDATE"

        print(f"{name} (GB{vat}) -> {status} (HMRC: '{hmrc_name}')")

        results.append({"company_name": name, "company_number": number,
                         "candidate_vat": vat, "hmrc_registered_name": hmrc_name,
                         "status": status})

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

        time.sleep(DELAY_SECONDS)

    matches = sum(1 for r in results if r["status"] == "MATCH_CONFIRMED")
    false_c = sum(1 for r in results if r["status"] == "FALSE_CANDIDATE")
    rate_l = sum(1 for r in results if r["status"] == "RATE_LIMITED")
    print(f"\n{'=' * 50}")
    print(f"Verified so far      : {len(results)}/{len(discovered)}")
    print(f"MATCH_CONFIRMED      : {matches}")
    print(f"FALSE_CANDIDATE      : {false_c}")
    print(f"RATE_LIMITED (retry later): {rate_l}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run()