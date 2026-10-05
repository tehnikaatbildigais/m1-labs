"""Personas koda pārbaude (CR-1).

Derīgi divi formāti, abi tieši 11 cipari bez defises:
- vecais: DDMMGG + gadsimta cipars (0 = 1800., 1 = 1900., 2 = 2000.) + 3 cipari
  + kontrolcipars. Datumam jāeksistē un jābūt ne vēlākam par šodienu.
- jaunais (no 2017. gada): "32" + 9 cipari. Dzimšanas datuma un kontrolcipara nav.
"""

import re
from datetime import date

WEIGHTS = (1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
CENTURIES = {"0": 1800, "1": 1900, "2": 2000}
_DIGITS_11 = re.compile(r"[0-9]{11}")  # \d pieņemtu arī citu rakstību ciparus


def check_digit(first_ten: str) -> int:
    """Vecā formāta kontrolcipars. Rezultāts 10 nozīmē, ka šāds kods nav derīgs."""
    total = sum(w * int(d) for w, d in zip(WEIGHTS, first_ten, strict=True))
    return (1101 - total) % 11


def birth_date(code: str) -> date | None:
    century = CENTURIES.get(code[6])
    if century is None:
        return None
    try:
        return date(century + int(code[4:6]), int(code[2:4]), int(code[0:2]))
    except ValueError:
        return None


def is_valid(code: str, today: date | None = None) -> bool:
    if not _DIGITS_11.fullmatch(code):
        return False
    if code.startswith("32"):
        return True
    born = birth_date(code)
    if born is None or born > (today or date.today()):
        return False
    return check_digit(code[:10]) == int(code[10])
