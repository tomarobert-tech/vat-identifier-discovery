import re
import urllib3
import requests
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# --- 1. VALIDARE MATEMATICĂ (MODULUS 97) ---
def is_valid_vat_checksum(vat_digits: str) -> bool:
    """Validează checksum-ul unui VAT UK (9 cifre), algoritmul modulus 97."""
    if len(vat_digits) != 9 or not vat_digits.isdigit():
        return False
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(w * int(d) for w, d in zip(weights, vat_digits[:7]))
    check_digits = int(vat_digits[7:9])

    check_old = (97 - total % 97) % 97
    check_new = (97 - (total + 55) % 97) % 97

    return check_digits in (check_old, check_new)


# --- 2. VERIFICARE OFICIALĂ HMRC (VALIDATĂ) ---
def verify_hmrc_vat_robust(vat_number):
    """Verifică un număr de VAT prin HMRC folosind fluxul complet cu sesiune + CSRF + parametrul 'target'."""
    session = requests.Session()
    session.headers.update(HEADERS)
    start_url = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"

    try:
        # Pasul 1: Preluare CSRF Token
        res_init = session.get(start_url, timeout=10)
        if res_init.status_code != 200:
            return None

        soup_init = BeautifulSoup(res_init.text, "html.parser")
        csrf_input = soup_init.find("input", {"name": "csrfToken"})
        if not csrf_input:
            return None

        csrf_token = csrf_input.get("value")

        # Pasul 2: Trimitere POST cu parametrul 'target'
        payload = {
            "csrfToken": csrf_token,
            "target": str(vat_number),
            "requester": "",
        }

        res_post = session.post(
            start_url, data=payload, timeout=10, allow_redirects=True
        )

        # Pasul 3: Extragere nume prin Regex pe Textul Curățat
        if res_post.status_code == 200:
            soup_res = BeautifulSoup(res_post.text, "html.parser")
            text_clean = " ".join(soup_res.get_text().split())

            match = re.search(
                r"Registered business name\s+(.*?)\s+Registered business address",
                text_clean,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()

            if "valid uk vat number" in text_clean.lower():
                return "VALID_VAT_CONFIRMED"

    except Exception as e:
        print(f"Eroare verificare HMRC: {e}")

    return None


if __name__ == "__main__":
    print("=== TESTARE IZOLATĂ REPARATĂ ===")

    # Test 0: Modulus 97 Checksum
    bt_vat = "245719348"
    print(f"0. Checksum Modulus 97 for {bt_vat}: {is_valid_vat_checksum(bt_vat)}")

    # Test 1: HMRC Verification
    print("\n--- Test 1: HMRC Verification (Sesiune + CSRF + Regex Parser) ---")
    hmrc_res = verify_hmrc_vat_robust(bt_vat)
    print(f"Rezultat HMRC pentru {bt_vat}: '{hmrc_res}'")