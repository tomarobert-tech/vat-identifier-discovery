"""
Debug izolat pentru sursa vat-lookup.co.uk.
Rulează ASTA local (nu în sandbox) - salvează răspunsul brut pe disc
ca să poți inspecta exact ce se întoarce, nu doar ce spune codul despre el.
"""

import requests
from pipeline import is_valid_vat_checksum, HEADERS

URL = "https://vat-lookup.co.uk/verify/search.php"

# O companie mare, deja confirmată manual (Faza 2) că are VAT găsibil ușor,
# plus 2-3 companii random din eșantionul tău de 300 (copiate din sample_companies.json).
TEST_CASES = [
    "British Telecommunications",   # control pozitiv - ar trebui sa mearga daca sursa functioneaza deloc
    "EDELWEISS (CHEDDAR) LIMITED",  # inlocuieste cu 2-3 nume reale din sample_companies.json
]

BLOCKING_SIGNALS = [
    "captcha", "cloudflare", "access denied", "blocked",
    "just a moment", "unusual traffic", "rate limit",
]


def debug_one(company_name: str, idx: int):
    print(f"\n{'=' * 60}\nTestez: {company_name}\n{'=' * 60}")

    # 1. Cerere fara header custom - vezi daca User-Agent-ul conteaza
    for label, headers in [("CU HEADERS", HEADERS), ("FARA HEADERS", {})]:
        try:
            res = requests.post(
                URL, data={"CompanyName": company_name},
                headers=headers, timeout=10, allow_redirects=True,
            )
        except Exception as e:
            print(f"  [{label}] EROARE cerere: {e}")
            continue

        body_lower = res.text.lower()
        signals = [s for s in BLOCKING_SIGNALS if s in body_lower]
        gb_matches = __import__("re").findall(r"GB\s?(\d{9})", res.text)
        valid_checksums = [m for m in gb_matches if is_valid_vat_checksum(m)]

        print(f"  [{label}]")
        print(f"    status_code      : {res.status_code}")
        print(f"    url final        : {res.url}")
        print(f"    content-type     : {res.headers.get('content-type')}")
        print(f"    lungime raspuns  : {len(res.text)} caractere")
        print(f"    semnale blocare  : {signals or 'niciunul detectat'}")
        print(f"    contine 'Sorry'  : {'Sorry' in res.text}")
        print(f"    GB+9cifre gasite : {gb_matches}")
        print(f"    valid checksum   : {valid_checksums}")

        # Salvezi raspunsul brut ca sa te uiti direct in el
        fname = f"debug_response_{idx}_{label.replace(' ', '_')}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(res.text)
        print(f"    salvat in        : {fname}  <- deschide-l in browser sau editor")


if __name__ == "__main__":
    for i, name in enumerate(TEST_CASES, 1):
        debug_one(name, i)

    print(
        "\n\nCum interpretezi rezultatul:\n"
        "- Daca British Telecommunications da GB+9cifre valide, dar compania random nu -> "
        "sursa chiar nu acopera companii mici (dead-end real, documentezi cu cifre).\n"
        "- Daca NICIUNA nu da nimic, dar lungimea raspunsului e mica/suspecta sau apar "
        "semnale de blocare -> esti blocat, nu ai un rezultat real inca. Incearca de pe alta retea "
        "(alt IP), cu delay mai mare intre cereri, sau verifica manual in browser daca formularul "
        "mai e la fel.\n"
        "- Deschide fisierele .html salvate - daca arata ca o pagina de eroare generica sau un "
        "ecran gol, e semn clar de blocare, nu de 'lipsa date'.\n"
    )