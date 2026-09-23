import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tax.service.gov.uk/check-vat-number/enter-vat-details"


def extract_vat_result(soup):
    """Extrage câmpurile dintr-o pagină de rezultat VAT bazată pe structura govuk-heading-s."""
    result = {}

    # Căutăm toate titlurile h3 care au clasa 'govuk-heading-s'
    headings = soup.find_all("h3", class_="govuk-heading-s")

    for heading in headings:
        key = heading.get_text(strip=True)

        # Valoarea se află în următorul element frate (sibling), de obicei un <p> sau <div>
        next_elem = heading.find_next_sibling()
        if next_elem:
            value = next_elem.get_text(separator=" ", strip=True)
            result[key] = value

    return result


def check_vat_number_public(vat_number: str):
    session = requests.Session()

    # Pasul 1: GET — setează cookie-ul de sesiune și ne dă csrfToken-ul
    response_get = session.get(BASE_URL)
    soup = BeautifulSoup(response_get.text, "html.parser")

    csrf_input = soup.find("input", {"name": "csrfToken"})
    csrf_token = csrf_input["value"] if csrf_input else None

    if not csrf_token:
        print("Nu am găsit csrfToken în pagină")
        return None

    # Pasul 2: POST cu cele 3 câmpuri reale găsite de tine
    payload = {
        "csrfToken": csrf_token,
        "target": vat_number,
        "requester": "",  # gol — nu solicităm dovadă de verificare
    }
    response_post = session.post(BASE_URL, data=payload)

    # Pasul 3: parsăm pagina de rezultat și apelăm funcția dedicată (exact ca în cerință)
    result_soup = BeautifulSoup(response_post.text, "html.parser")
    date_extrase = extract_vat_result(result_soup)

    print(date_extrase)
    return date_extrase


if __name__ == "__main__":
    check_vat_number_public("GB245719348")