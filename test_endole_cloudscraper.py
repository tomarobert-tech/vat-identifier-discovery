"""
PASUL 1 - incearca sa treci de Cloudflare pe Endole cu cloudscraper.
Ruleaza asta INTAI, pe putine companii, ca sa vezi rapid daca merita continuat.
Daca in 10-15 minute tot iei 403/challenge, abandonezi si treci la Pasul 2 (DuckDuckGo).

pip install cloudscraper
"""

import time
import cloudscraper
from test_endole_source import slugify, VAT_PATTERN
from verify_helper import verify_candidate

scraper = cloudscraper.create_scraper()

# Testezi intai doar pe astea 3 - una unde STII ca exista VAT (control), doua din esantion
TEST_CASES = [
    ("09905931", "Ineo Nuclear UK Ltd"),   # control pozitiv - stim ca are VAT: GB365998427
    ("04169780", "Globe UK Holding Ltd"),
    ("13547774", "Ozero Tech Ltd"),
]

for number, name in TEST_CASES:
    url = f"https://open.endole.co.uk/insight/company/{number}-{slugify(name)}"
    try:
        res = scraper.get(url, timeout=15)
    except Exception as e:
        print(f"{name}: EROARE - {e}")
        continue

    print(f"\n{name}")
    print(f"  status: {res.status_code}")
    print(f"  lungime: {len(res.text)}")

    if res.status_code == 200:
        match = VAT_PATTERN.search(res.text)
        if match:
            candidate = match.group(1)
            r = verify_candidate(candidate, name, "endole-cloudscraper")
            print(f"  CANDIDAT GASIT: {candidate} -> {r['verdict']}")
        else:
            print("  200 OK, dar niciun VAT Number gasit pe pagina")
    else:
        print(f"  Tot blocat (status {res.status_code}) - cloudscraper n-a rezolvat problema")

    time.sleep(2)