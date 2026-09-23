"""
PASUL 2 - automatizeaza exact ce ai facut manual pentru Ineo Nuclear:
cauti "<nume companie> VAT number" pe DuckDuckGo, deschizi primele cateva rezultate,
cauti un pattern VAT pe pagina, verifici prin verify_helper.

Ruleaza INTAI cu TEST_SIZE mic (20-30) ca sa vezi rata de succes reala inainte
sa pornesti pe toate cele 300 - dureaza mult (fiecare companie = 1 cautare + pana la
3 fetch-uri de pagina, cu delay-uri).
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from verify_helper import verify_candidate

INPUT_SAMPLE = "sample_companies.json"
OUTPUT_RESULTS = "ddg_pipeline_results.json"
TEST_SIZE = 25          # incepe mic
MAX_RESULTS_PER_COMPANY = 3   # cate linkuri din cautare incerci per companie
REQUEST_DELAY = 2       # secunde intre cereri - nu grabi

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.5",
}

VAT_NEAR_PATTERN = re.compile(r"VAT[^0-9]{0,25}GB\s?(\d{9})", re.IGNORECASE)
VAT_ANY_PATTERN = re.compile(r"\bGB\s?(\d{9})\b")


def ddg_search_urls(query: str) -> list:
    """Cauta pe DuckDuckGo HTML si intoarce linkurile din rezultate (cele organice)."""
    url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
    except Exception as e:
        print(f"   [DEBUG] eroare cautare: {e}")
        return []

    if res.status_code != 200:
        print(f"   [DEBUG] status cautare: {res.status_code}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    links = []
    for a in soup.select("a.result__a")[:MAX_RESULTS_PER_COMPANY]:
        href = a.get("href")
        if href:
            links.append(href)
    return links


def scan_page_for_vat(url: str):
    """Deschide o pagina si cauta un pattern VAT. Prefera pattern-ul 'VAT ... GB123456789'
    (mai sigur), cade pe orice GB+9cifre doar daca nu gaseste nimic mai specific."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
    except Exception:
        return None

    if res.status_code != 200:
        return None

    match = VAT_NEAR_PATTERN.search(res.text)
    if match:
        return match.group(1)

    match = VAT_ANY_PATTERN.search(res.text)
    if match:
        return match.group(1)

    return None


def run_pipeline():
    with open(INPUT_SAMPLE, "r", encoding="utf-8") as f:
        companies = json.load(f)[:TEST_SIZE]

    results = []
    coverage = 0
    matches = 0
    false_positives = 0

    for idx, comp in enumerate(companies, 1):
        name = comp["company_name"]
        print(f"\n[{idx}/{len(companies)}] {name}")

        urls = ddg_search_urls(f'"{name}" VAT number')
        time.sleep(REQUEST_DELAY)

        candidate = None
        source_url = None
        for url in urls:
            candidate = scan_page_for_vat(url)
            if candidate:
                source_url = url
                break
            time.sleep(REQUEST_DELAY)

        if not candidate:
            print("   niciun candidat gasit")
            results.append({**comp, "candidate_vat": None, "verdict": "NO_CANDIDATE"})
            continue

        coverage += 1
        r = verify_candidate(candidate, name, "duckduckgo-scan")
        r["source_url"] = source_url
        print(f"   candidat: {candidate} -> {r['verdict']} "
              f"(HMRC: '{r['hmrc_name']}', similaritate: {r['name_similarity']})")

        if r["verdict"] == "MATCH":
            matches += 1
        elif r["verdict"] == "FALSE_POSITIVE_NAME_MISMATCH":
            false_positives += 1

        results.append({**comp, **r})

        # salvezi incremental, ca sa nu pierzi tot daca pica ceva la jumatate
        with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    total = len(companies)
    print(f"\n{'=' * 50}")
    print(f"Total testate           : {total}")
    print(f"Coverage (candidat gasit): {coverage}/{total} ({100 * coverage / total:.1f}%)")
    print(f"Match confirmat          : {matches}")
    print(f"Fals-pozitiv             : {false_positives}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    run_pipeline()