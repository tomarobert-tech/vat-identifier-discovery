from pipeline import search_candidate_vat, verify_hmrc_vat

# Companii mari, unde ai confirmat deja manual (Google) că VAT-ul e găsibil
companii_test = [
    "British Telecommunications",
    "British Airways",
    "Vodafone",
    "Tesco",
    "BP",
]

for nume in companii_test:
    print(f"\n=== Testez: {nume} ===")
    candidat = search_candidate_vat(nume)

    if candidat:
        print(f"   Candidat găsit: GB{candidat}")
        nume_hmrc = verify_hmrc_vat(candidat)
        if nume_hmrc:
            print(f"   ✅ Confirmat HMRC: {nume_hmrc}")
        else:
            print("   ❌ Respins de HMRC")
    else:
        print("   ⚪ Niciun candidat găsit")