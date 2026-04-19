
import re
from typing import Tuple


KNOWN_CORRECTIONS = {
    "tit1e": "title",
    "T1TLE": "TITLE",
    "fi1e": "file",
    "Fi1e": "File",
    "fo11owing": "following",
    "po1icy": "policy",
    "origina1": "original",
    "1ien": "lien",
    "payab1e": "payable",
    "Parce1": "Parcel",
    "Pa1metto": "Palmetto",
    "F1orida": "Florida",
    "e1ectrica1": "electrical",
    "1ines": "lines",
    "simp1e": "simple",
    "sing1e": "single",
    "Officia1": "Official",
    "EXCEPT1ONS": "EXCEPTIONS",
    "RODR1GUEZ": "RODRIGUEZ",
    "fi1ed": "filed",
    "PALMETT0": "PALMETTO",
    "ASSOCIATI0N": "ASSOCIATION",
    "WE11S": "WELLS",
    "Car1os": "Carlos",
}


def fix_known_words(text: str) -> Tuple[str, list[str]]:
    """Replace known OCR-corrupted words with corrections."""
    corrections = []
    for bad, good in KNOWN_CORRECTIONS.items():
        if bad in text:
            count = text.count(bad)
            text = text.replace(bad, good)
            corrections.append(f"'{bad}' → '{good}' ({count}x)")
    return text, corrections


def fix_numeric_o_to_zero(text: str) -> Tuple[str, list[str]]:
    """Fix 'O' used in place of '0' in numeric contexts.

    """
    corrections = []

    def fix_dollar(m):
        original = m.group(0)
        fixed = original.replace("O", "0")
        if fixed != original:
            corrections.append(f"'{original}' → '{fixed}' (dollar amount)")
        return fixed

    text = re.sub(r"\$[\d,O]+\.O{1,2}", fix_dollar, text)
    text = re.sub(r"\$[\d,O]+(?=[\s\n,;)])", fix_dollar, text)

    def fix_year(m):
        original = m.group(0)
        fixed = original.replace("O", "0")
        if fixed != original:
            corrections.append(f"'{original}' → '{fixed}' (year)")
        return fixed

    text = re.sub(r"\b[12][O0]\d[O0]\b", fix_year, text)

    def fix_instrument(m):
        original = m.group(0)
        fixed = original.replace("O", "0")
        if fixed != original:
            corrections.append(f"'{original}' → '{fixed}' (instrument no.)")
        return fixed

    text = re.sub(r"\b\d{2,4}-O[\dO]+\b", fix_instrument, text)
    text = re.sub(r"\b2O\d{2}-[\dO]+\b", fix_instrument, text)

    def fix_parcel(m):
        original = m.group(0)
        fixed = original.replace("O", "0")
        if fixed != original:
            corrections.append(f"'{original}' → '{fixed}' (parcel no.)")
        return fixed

    text = re.sub(r"\b\d{1,3}-[O\d]{3,5}-[O\d]{2,4}-[O\d]{3,5}\b", fix_parcel, text)

    def fix_book(m):
        prefix = m.group(1)
        num = m.group(2).replace("O", "0")
        result = prefix + num
        if result != m.group(0):
            corrections.append(f"'{m.group(0)}' → '{result}' (book/page ref)")
        return result

    text = re.sub(r"(Book |Page )([\dO]+)", fix_book, text)

    return text, corrections


def fix_l_to_one_in_words(text: str) -> Tuple[str, list[str]]:
    """Fix remaining '1' used as 'l' inside words (catch-all)."""
    corrections = []

    def replace_one_with_l(m):
        word = m.group(0)
        if re.match(r"^\d+$", word) or re.match(r"^\d+-", word):
            return word
        fixed = ""
        for i, ch in enumerate(word):
            if ch == "1" and i > 0 and i < len(word) - 1:
                if word[i - 1].isalpha() and word[i + 1].isalpha():
                    fixed += "l"
                    continue
            fixed += ch
        if fixed != word:
            corrections.append(f"'{word}' → '{fixed}' (1→l in word)")
        return fixed

    text = re.sub(r"\b[A-Za-z][A-Za-z1]+[A-Za-z]\b", replace_one_with_l, text)
    return text, corrections


def clean_ocr_text(text: str) -> Tuple[str, list[str]]:
    """Full OCR cleaning pipeline. Returns (cleaned_text, list_of_corrections)."""
    all_corrections = []

    text, corr = fix_known_words(text)
    all_corrections.extend(corr)

    text, corr = fix_numeric_o_to_zero(text)
    all_corrections.extend(corr)

    text, corr = fix_l_to_one_in_words(text)
    all_corrections.extend(corr)

    seen = set()
    unique = []
    for c in all_corrections:
        if c not in seen:
            seen.add(c)
            unique.append(c)

    return text, unique
