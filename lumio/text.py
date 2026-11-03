import re
import unicodedata

_STOPWORDS = {"de", "du", "des", "la", "le", "les", "l", "d", "et", "sa", "sas", "sarl", "selarl"}


def normalize(text: str) -> str:
    """Minuscules, sans accents ni ponctuation."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_text = decomposed.encode("ascii", "ignore").decode().lower()
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def significant_tokens(text: str) -> set[str]:
    return set(normalize(text).split()) - _STOPWORDS
