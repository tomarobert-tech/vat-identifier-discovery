"""
Shared verification helper for any candidate-VAT source (vat-lookup.co.uk,
Endole, EORI, website disclosure, etc.). Runs the full chain: checksum ->
HMRC -> name comparison - so every source is checked the same way, and the
results are comparable across sources, and a false positive rate can
actually be calculated (as required by the brief).

Requires pipeline.py in the same folder (uses is_valid_vat_checksum and
verify_hmrc_vat from there).
"""

import re
import difflib
from pipeline import is_valid_vat_checksum, verify_hmrc_vat

LEGAL_SUFFIXES = {
    "LIMITED", "LTD", "PLC", "LLP", "LP", "CIC", "CIO", "CO",
}


def normalize_name(name: str) -> str:
    """Uppercase, strips punctuation and common legal suffixes (LTD/LIMITED/etc.),
    so that 'J Smith Building Services Ltd' compares against
    'J. SMITH BUILDING SVCS LIMITED' on substance, not exact wording."""
    name = name.upper()
    name = re.sub(r"[.,'&()]", " ", name)
    words = [w for w in name.split() if w not in LEGAL_SUFFIXES]
    return " ".join(words).strip()


def name_similarity(name_a: str, name_b: str) -> float:
    """Similarity score (0-1) between two names, after normalisation."""
    return difflib.SequenceMatcher(
        None, normalize_name(name_a), normalize_name(name_b)
    ).ratio()


def verify_candidate(vat_digits: str, expected_company_name: str, source: str,
                      match_threshold: float = 0.6) -> dict:
    """
    Full verification pipeline for ONE candidate VAT number from any source.

    Returns a dict with a verdict, one of:
      - CHECKSUM_INVALID          -> fails the math check, rejected for free
      - HMRC_REJECTED             -> checksum ok, but HMRC does not confirm an active VAT
      - HMRC_CONFIRMED_NO_NAME    -> HMRC confirms valid, but no name could be extracted (check manually)
      - MATCH                     -> HMRC confirms, and the name matches the expected company
      - FALSE_POSITIVE_NAME_MISMATCH -> HMRC confirms a valid VAT, but it belongs to a
                                        different company (the exact risk the brief warns about -
                                        a plausible number attached to the wrong company)
    """
    result = {
        "source": source,
        "expected_company_name": expected_company_name,
        "candidate_vat": vat_digits,
        "checksum_valid": False,
        "hmrc_name": None,
        "name_similarity": 0.0,
        "verdict": "CHECKSUM_INVALID",
    }

    if not vat_digits or not is_valid_vat_checksum(vat_digits):
        return result
    result["checksum_valid"] = True

    hmrc_name = verify_hmrc_vat(vat_digits)
    result["hmrc_name"] = hmrc_name

    if not hmrc_name:
        result["verdict"] = "HMRC_REJECTED"
        return result

    if hmrc_name == "VALID_VAT_CONFIRMED":
        result["verdict"] = "HMRC_CONFIRMED_NO_NAME"
        return result

    score = name_similarity(hmrc_name, expected_company_name)
    result["name_similarity"] = round(score, 2)
    result["verdict"] = "MATCH" if score >= match_threshold else "FALSE_POSITIVE_NAME_MISMATCH"
    return result