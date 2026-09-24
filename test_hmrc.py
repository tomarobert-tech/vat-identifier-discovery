"""
Tests HMRC's official sandbox (test) environment for the "Check a UK VAT
Number" API, using OAuth2 client credentials from .env.

This is the script behind the finding in README.md (Technical Foundations,
point 1): the sandbox only recognises a small set of mock VAT numbers made
for testing (using the "Gov-Test-Scenario: SUCCESS" header below), not real
ones - so it could not be used for actual verification, which is why the
project relies on the public web checker instead (see main.py, pipeline.py).
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# load environment variables from the .env file
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

CLIENT_ID = os.getenv("HMRC_CLIENT_ID")
CLIENT_SECRET = os.getenv("HMRC_CLIENT_SECRET")

TOKEN_URL = "https://test-api.service.hmrc.gov.uk/oauth/token"
LOOKUP_URL = "https://test-api.service.hmrc.gov.uk/organisations/vat/check-vat-number/lookup"


def get_access_token(client_id: str, client_secret: str) -> str:
    """Gets an Access Token from HMRC's Sandbox OAuth2 server."""
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }

    response = requests.post(TOKEN_URL, data=payload, headers=headers)

    if response.status_code == 200:
        token = response.json().get("access_token")
        print("OAuth2 token obtained successfully!")
        return token
    else:
        print(f"Token error {response.status_code}: {response.text}")
        return None


def check_vat_number(vat_number: str, token: str):
    """Checks a VAT number against HMRC's Sandbox."""
    headers = {
        "Accept": "application/vnd.hmrc.1.0+json",
        "Authorization": f"Bearer {token}",
        "Gov-Test-Scenario": "SUCCESS"
    }

    url = f"{LOOKUP_URL}/{vat_number}"
    response = requests.get(url, headers=headers)

    print(f"\nVAT lookup status code: {response.status_code}")

    if response.status_code == 200:
        print("VAT number validated successfully!")
        print(f"Response from HMRC: {response.json()}")
    elif response.status_code == 404:
        print("This VAT number was not found in the Sandbox registry.")
    else:
        print(f"API response: {response.status_code} - {response.text}")


if __name__ == "__main__":
    print("=== TESTING OAUTH2 & HMRC VAT API SANDBOX ===")
    token = get_access_token(CLIENT_ID, CLIENT_SECRET)

    if token:
        check_vat_number("555555555", token)