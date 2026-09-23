"""
De ce HMRC a respins 4 din 5 candidati gasiti corect pe vat-lookup.co.uk?
Verificam direct raspunsul brut de la HMRC pentru fiecare, ca sa vedem daca
spune explicit "nu e valid" sau daca cererea esueaza tehnic (sesiune/CSRF/parsare) -
aceeasi distinctie pe care am aplicat-o peste tot in proiect pana acum.
"""

import re
from bs4 import BeautifulSoup
import requests
from pipeline import HEADERS

REJECTED_CANDIDATES = [
    ("RAMONRA LTD", "314660128"),
    ("UMBERSLADE CORPORATE MANAGEMENT LIMITED DIRECTORS PENSION FUND", "559123631"),
    ("WPS LIVERPOOL LTD", "381634978"),
    ("SWIFTSURE DESIGN LIMITED", "144026249"),
]


def debug_hmrc_check(vat_number: str):
    session = requests.Session()
    session.headers.update(HEADERS)
    start_url = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"

    res_init = session.get(start_url, timeout=10)
    print(f"   GET initial: status {res_init.status_code}")

    soup_init = BeautifulSoup(res_init.text, "html.parser")
    csrf_input = soup_init.find("input", {"name": "csrfToken"})
    if not csrf_input:
        print("   NU am gasit csrfToken pe pagina initiala - posibila schimbare de structura")
        return
    csrf_token = csrf_input.get("value")
    print(f"   csrf token gasit: {csrf_token[:15]}...")

    payload = {"csrfToken": csrf_token, "target": vat_number, "requester": ""}
    res_post = session.post(start_url, data=payload, timeout=10, allow_redirects=True)
    print(f"   POST: status {res_post.status_code}, url final: {res_post.url}")

    soup_res = BeautifulSoup(res_post.text, "html.parser")
    text_clean = " ".join(soup_res.get_text().split())

    # afisam un fragment din text ca sa vedem EXACT ce spune HMRC
    print(f"   Text raspuns (primele 400 caractere):")
    print(f"   {text_clean[:400]}")
    print()


for name, vat in REJECTED_CANDIDATES:
    print(f"\n{'=' * 60}\n{name} - GB{vat}\n{'=' * 60}")
    debug_hmrc_check(vat)