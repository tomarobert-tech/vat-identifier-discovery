"""
An early, standalone test combining the checksum check and the HMRC
verification flow in one script, before they were merged into pipeline.py.
Tests both on British Telecommunications' known VAT number (GB245719348) as
a sanity check that the whole chain works end to end.
"""

import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# --- 1. MATH VALIDATION (MODULUS 97) ---
def is_valid_vat_checksum(vat_digits: str) -> bool:
    """Validates the checksum of a UK VAT number (9 digits), modulus 97 algorithm."""
    if len(vat_digits) != 9 or not vat_digits.isdigit():
        return False
    weights = [8, 7, 6, 5, 4, 3, 2]
    total = sum(w * int(d) for w, d in zip(weights, vat_digits[:7]))
    check_digits = int(vat_digits[7:9])

    check_old = (97 - total % 97) % 97
    check_new = (97 - (total + 55) % 97) % 97

    return check_digits in (check_old, check_new)


# --- 2. OFFICIAL HMRC VERIFICATION (VALIDATED) ---
def verify_hmrc_vat_robust(vat_number):
    """Verifies a VAT number through HMRC using the full session + CSRF + 'target' flow."""
    session = requests.Session()
    session.headers.update(HEADERS)
    start_url = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"

    try:
        # Step 1: get the CSRF token
        res_init = session.get(start_url, timeout=10)
        if res_init.status_code != 200:
            return None

        soup_init = BeautifulSoup(res_init.text, "html.parser")
        csrf_input = soup_init.find("input", {"name": "csrfToken"})
        if not csrf_input:
            return None

        csrf_token = csrf_input.get("value")

        # Step 2: send the POST with the 'target' field
        payload = {
            "csrfToken": csrf_token,
            "target": str(vat_number),
            "requester": "",
        }

        res_post = session.post(
            start_url, data=payload, timeout=10, allow_redirects=True
        )

        # Step 3: extract the name with regex, on the cleaned text
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
        print(f"HMRC verification error: {e}")

    return None


if __name__ == "__main__":
    print("=== ISOLATED TEST (FIXED) ===")

    # Test 0: Modulus 97 Checksum
    bt_vat = "245719348"
    print(f"0. Checksum Modulus 97 for {bt_vat}: {is_valid_vat_checksum(bt_vat)}")

    # Test 1: HMRC Verification
    print("\n--- Test 1: HMRC Verification (Session + CSRF + Regex Parser) ---")
    hmrc_res = verify_hmrc_vat_robust(bt_vat)
    print(f"HMRC result for {bt_vat}: '{hmrc_res}'")