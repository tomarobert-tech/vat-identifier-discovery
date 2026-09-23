import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Încărcăm variabilele de mediu din fișierul .env
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.getenv("HMRC_CLIENT_ID")
CLIENT_SECRET = os.getenv("HMRC_CLIENT_SECRET")

TOKEN_URL = "https://test-api.service.hmrc.gov.uk/oauth/token"
LOOKUP_URL = "https://test-api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup"

def get_access_token(client_id: str, client_secret: str) -> str:
    """Obține un Access Token de la serverul OAuth2 HMRC Sandbox."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    
    response = requests.post(TOKEN_URL, data=payload, headers=headers)
    
    if response.status_code == 200:
        token = response.json().get("access_token")
        print(" Token OAuth2 obținut cu succes!")
        return token
    else:
        print(f" Eroare Token {response.status_code}: {response.text}")
        return None

def check_vat_number(vat_number: str, token: str):
    """Verifică un număr de VAT pe HMRC Sandbox."""
    headers = {
        "Accept": "application/vnd.hmrc.1.0+json",
        "Authorization": f"Bearer {token}",
        "Gov-Test-Scenario": "SUCCESS"
    }
    
    url = f"{LOOKUP_URL}/{vat_number}"
    response = requests.get(url, headers=headers)
    
    print(f"\nStatus Code Interogare VAT: {response.status_code}")
    
    if response.status_code == 200:
        print(" Număr VAT Validat cu succes!")
        print(f" Răspuns de la HMRC: {response.json()}")
    elif response.status_code == 404:
        print(" Numărul de VAT nu a fost găsit în registrul Sandbox.")
    else:
        print(f" Răspuns API: {response.status_code} - {response.text}")

if __name__ == "__main__":
    print("=== TESTARE OAUTH2 & HMRC VAT API SANDBOX ===")
    token = get_access_token(CLIENT_ID, CLIENT_SECRET)
    
    if token:
        check_vat_number("555555555", token)