"""Canonical geography of Rwanda (5 provinces, 30 districts since the 2006 reform).

Source labels vary ("Southern", "South", "Southern Province", "Kigali City"),
so every parser maps names through :func:`canonical`.
"""
from __future__ import annotations

PROVINCES = {
    "kigali": "City of Kigali",
    "southern": "Southern Province",
    "western": "Western Province",
    "northern": "Northern Province",
    "eastern": "Eastern Province",
}

DISTRICTS_BY_PROVINCE = {
    "kigali": ["Nyarugenge", "Gasabo", "Kicukiro"],
    "southern": ["Nyanza", "Gisagara", "Nyaruguru", "Huye", "Nyamagabe", "Ruhango", "Muhanga", "Kamonyi"],
    "western": ["Karongi", "Rutsiro", "Rubavu", "Nyabihu", "Ngororero", "Rusizi", "Nyamasheke"],
    "northern": ["Rulindo", "Gakenke", "Musanze", "Burera", "Gicumbi"],
    "eastern": ["Rwamagana", "Nyagatare", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Bugesera"],
}

DISTRICT_PROVINCE = {d: p for p, ds in DISTRICTS_BY_PROVINCE.items() for d in ds}
DISTRICT_IDS = {d: d.lower() for d in DISTRICT_PROVINCE}

_PROVINCE_ALIASES = {
    "city of kigali": "kigali", "kigali city": "kigali", "kigali": "kigali",
    "southern": "southern", "south": "southern", "southern province": "southern",
    "western": "western", "west": "western", "western province": "western",
    "northern": "northern", "north": "northern", "northern province": "northern",
    "eastern": "eastern", "east": "eastern", "eastern province": "eastern",
}
_DISTRICT_ALIASES = {d.lower(): d for d in DISTRICT_PROVINCE}


def norm(label: object) -> str:
    return " ".join(str(label or "").replace("\xa0", " ").split()).strip()


def province_id(label: str) -> str | None:
    return _PROVINCE_ALIASES.get(norm(label).lower())


def district_name(label: str) -> str | None:
    return _DISTRICT_ALIASES.get(norm(label).lower())


def canonical(label: str) -> tuple[str, str, str] | None:
    """Return (level, geo_id, display_name) for a geographic label, or None."""
    lab = norm(label).lower()
    if lab in {"rwanda", "all rwanda", "national", "total", "poverty rate"}:
        return ("national", "rwanda", "Rwanda")
    if lab in {"urban", "rural"}:
        return ("area", lab, lab.title())
    pid = province_id(lab)
    if pid:
        return ("province", pid, PROVINCES[pid])
    d = district_name(lab)
    if d:
        return ("district", DISTRICT_IDS[d], d)
    return None
