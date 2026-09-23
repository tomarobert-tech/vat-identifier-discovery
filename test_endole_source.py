"""
Testeaza sursa endole.co.uk pe un esantion mai mare din sample_companies.json,
folosind pattern-ul predictibil de URL: /insight/company/{numar_companie}-{slug_nume}.

Important - citeste inainte sa rulezi pe tot esantionul:
- Endole e un produs comercial (sales intelligence / lead generation), nu o sursa
  guvernamentala primara. Are Termeni de Utilizare proprii. Pentru un PoC/challenge
  e o zona gri acceptabila de explorat, dar NU e automat o sursa OK de folosit
  intr-un produs comercial fara research de licentiere - discuta asta explicit in
  eseul de debate topics (Faza 7).
- Pui un delay intre cereri (implicit 2s) ca sa nu incarci serverul lor degeaba -
  e un singur laptop, nu ai nevoie de viteza, ai nevoie de rezultat corect.
- Ruleaza INTAI pe un esantion mic (ex. 30-50), nu pe toate cele 300 direct -
  vezi mai jos SAMPLE_SIZE.
"""

import json
import re
import time
import requests
from verify_helper import verify_candidate

INPUT_SAMPLE = "sample_companies.json"
OUTPUT_RESULTS = "endole_results.json"
SAMPLE_SIZE = 40  # incepe mic, mareste doar daca rezultatele arata promitator

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
}

VAT_PATTERN = re.compile(r"VAT Number\D{0,20}GB\s?(\d{9})", re.IGNORECASE)


def slugify(name: str) -> str:
    """Transforma numele companiei in formatul de slug folosit de Endole in URL."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return name.strip("-")


def fetch_endole_vat(company_number: str, company_name: str):
    """Incearca sa gaseasca un VAT Number pe pagina Endole a companiei.
    Intoarce (candidat_9_cifre_sau_None, status_code, lungime_raspuns)."""
    url = f"https://open.endole.co.uk/insight/company/{company_number}-{slugify(company_name)}"

    try:
        res = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
    except Exception as e:
        print(f"   [DEBUG] Eroare cerere: {e}")
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

    print(f"Testez Endole.co.uk pe {len(companies)} companii...\n")

    for idx, comp in enumerate(companies, 1):
        name = comp["company_name"]
        number = comp["company_number"]

        candidate, status, length = fetch_endole_vat(number, name)
        print(f"[{idx}/{len(companies)}] {name} -> "
              f"status {status}, candidat: {candidate}")

        if candidate:
            coverage += 1
            r = verify_candidate(candidate, name, "endole.co.uk")
            print(f"   verdict: {r['verdict']} (HMRC: '{r['hmrc_name']}', "
                  f"similaritate: {r['name_similarity']})")
            if r["verdict"] == "MATCH":
                matches += 1
            elif r["verdict"] == "FALSE_POSITIVE_NAME_MISMATCH":
                false_positives += 1
            results.append({**comp, **r})
        else:
            results.append({**comp, "candidate_vat": None, "verdict": "NO_CANDIDATE"})

        time.sleep(2)  # delay politicos - nu grabi, nu incarca degeaba serverul lor

    with open(OUTPUT_RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    total = len(companies)
    print(f"\n{'=' * 50}")
    print(f"Total testate         : {total}")
    print(f"Coverage (candidat gasit): {coverage}/{total} ({100 * coverage / total:.1f}%)")
    print(f"Match confirmat        : {matches}")
    print(f"Fals-pozitiv           : {false_positives}")
    print(f"{'=' * 50}")
    print(f"Rezultate salvate in '{OUTPUT_RESULTS}'")


if __name__ == "__main__":
    run_endole_test()