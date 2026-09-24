"""
main.py

The very first working version of the HMRC verification flow, built before
pipeline.py and pipeline_fixed.py existed. This is where the session/CSRF flow
and the exact form field names (`target`, `requester`) were first figured out,
by watching real requests in the browser's Network tab (see README, Technical
Foundations, point 2).

This script parses the result page differently from what the final pipeline
uses: it reads values from HTML headings (`h3.govuk-heading-s`) rather than
searching the page text with a regex (pipeline.py) or checking the response
URL (pipeline_fixed.py). Kept as-is, as the first working proof that
verification could be automated at all - not used by the final pipeline.
"""

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"


def extract_vat_result(soup):
    """Extracts the fields from a VAT result page, based on the
    govuk-heading-s structure."""
    result = {}

    # find every h3 heading with the 'govuk-heading-s' class
    headings = soup.find_all("h3", class_="govuk-heading-s")

    for heading in headings:
        key = heading.get_text(strip=True)

        # the value sits in the next sibling element, usually a <p> or <div>
        next_elem = heading.find_next_sibling()
        if next_elem:
            value = next_elem.get_text(separator=" ", strip=True)
            result[key] = value

    return result


def check_vat_number_public(vat_number: str):
    session = requests.Session()

    # Step 1: GET - sets the session cookie and gives us the csrfToken
    response_get = session.get(BASE_URL)
    soup = BeautifulSoup(response_get.text, "html.parser")

    csrf_input = soup.find("input", {"name": "csrfToken"})
    csrf_token = csrf_input["value"] if csrf_input else None

    if not csrf_token:
        print("Could not find csrfToken on the page")
        return None

    # Step 2: POST with the 3 real fields found in the browser's Network tab
    payload = {
        "csrfToken": csrf_token,
        "target": vat_number,
        "requester": "",  # left empty - not requesting proof of verification
    }
    response_post = session.post(BASE_URL, data=payload)

    # Step 3: parse the result page
    result_soup = BeautifulSoup(response_post.text, "html.parser")
    extracted_data = extract_vat_result(result_soup)

    print(extracted_data)
    return extracted_data


if __name__ == "__main__":
    check_vat_number_public("GB245719348")