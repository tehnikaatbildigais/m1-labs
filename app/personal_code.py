"""Personas koda pārbaude (CR-1).

Pārbauda tikai formātu, ne dzimšanas datumu, ne kontrolciparu:
- visas atstarpes tiek noņemtas;
- derīgs ir "NNNNNNNNNNN" (11 cipari) vai "NNNNNN-NNNNN";
- saglabā 11 ciparus bez defises.
"""

import re

_WHITESPACE = re.compile(r"\s+")  # arī tabulēšana un nedalāmā atstarpe
_FORMAT = re.compile(r"[0-9]{6}-?[0-9]{5}")  # \d pieņemtu arī citu rakstību ciparus


def compact(value: str) -> str:
    """Noņem visas atstarpes."""
    return _WHITESPACE.sub("", value)


def normalize(value: str) -> str | None:
    """Atgriež 11 ciparus bez defises vai None, ja formāts nav derīgs."""
    code = compact(value)
    if not _FORMAT.fullmatch(code):
        return None
    return code.replace("-", "")
