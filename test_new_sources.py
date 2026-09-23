"""
Testare Faza 2 pentru doua surse noi: EORI si publicare legala pe website
(Provision of Services Regulations 2009).

Cum lucrezi cu fisierul asta:
1. Cauti manual (web, agregatoare de comert, site-uri de companii) candidati pentru
   8-10 companii din sample_companies.json.
2. Completezi listele de mai jos cu ce ai gasit (sau None daca n-ai gasit nimic - e un
   rezultat valid, nu-l omite).
3. Rulezi scriptul - iti face verificarea completa (checksum + HMRC + comparare nume)
   si iti da un rezumat pe care il copiezi direct in jurnalul de cercetare.
"""

from verify_helper import verify_candidate

# --- SURSA A: EORI ---
# Format oficial confirmat (gov.uk/guidance/economic-operators-registration-and-identification-eori):
# EORI = "GB" + (9 cifre VAT) + "000" pentru companii inregistrate la VAT.
# Aici pui doar cele 9 cifre din mijloc (fara GB, fara 000 final).

EORI_TEST_CASES = [
    # (nume_companie_exact_din_esantion, cifre_vat_din_eori_sau_None)
    ("INEO NUCLEAR UK LTD", "365998427"),  # control pozitiv - stim deja ca e corect
    # adauga aici 8-10 companii reale din sample_companies.json
]

# --- SURSA B: VAT publicat pe website-ul companiei ---
# Cauti site-ul companiei, apoi in footer / Terms / Legal / About, un pattern gen
# "VAT No: GB123456789" sau "VAT Reg. No 123456789". Pui aici doar cele 9 cifre.

WEBSITE_TEST_CASES = [ None
    # (nume_companie_exact_din_esantion, cifre_vat_gasite_pe_site_sau_None)
]


def run_source_test(cases, source_name):
    print(f"\n{'=' * 60}\nSURSA: {source_name}\n{'=' * 60}")
    results = []

    for company_name, candidate in cases:
        if not candidate:
            print(f"{company_name}: NICIUN CANDIDAT GASIT")
            results.append({"verdict": "NO_CANDIDATE"})
            continue

        r = verify_candidate(candidate, company_name, source_name)
        print(
            f"{company_name}: {r['verdict']} "
            f"(HMRC: '{r['hmrc_name']}', similaritate nume: {r['name_similarity']})"
        )
        results.append(r)

    total = len(results)
    no_cand = sum(1 for r in results if r["verdict"] == "NO_CANDIDATE")
    matches = sum(1 for r in results if r["verdict"] == "MATCH")
    false_pos = sum(1 for r in results if r["verdict"] == "FALSE_POSITIVE_NAME_MISMATCH")
    hmrc_rejected = sum(1 for r in results if r["verdict"] == "HMRC_REJECTED")

    print(f"\n--- Rezumat {source_name} ---")
    print(f"Total testate                         : {total}")
    print(f"Coverage (candidat gasit)              : {total - no_cand}/{total}")
    print(f"Match confirmat (nume se potriveste)   : {matches}")
    print(f"Fals-pozitiv (VAT valid, alta companie): {false_pos}")
    print(f"Respins de HMRC                        : {hmrc_rejected}")

    return results


if __name__ == "__main__":
    run_source_test(EORI_TEST_CASES, "EORI")
    run_source_test(WEBSITE_TEST_CASES, "Website VAT disclosure")