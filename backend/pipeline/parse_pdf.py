"""Parsers for official PDF publications without Excel tables (FinScope 2024, Census 2022).

Values are extracted programmatically from the PDF text layer. Where the PDF text
merges two chart labels (e.g. "21" for adjacent 2 and 1 segments), a documented
resolution is applied ONLY if the raw extracted string matches exactly; resolutions
were verified by visually inspecting the rendered figure. Unlabelled segments stay
missing — they are never imputed as zero.
"""
from __future__ import annotations

import re

import pdfplumber

from .geography import DISTRICT_IDS, DISTRICT_PROVINCE, PROVINCES, canonical
from .model import Obs

STRAND = ["fs_banked", "fs_other_formal", "fs_informal_only", "fs_excluded"]

# raw extracted label string -> verified segment values (banked, other formal, informal only, excluded)
LABEL_RESOLUTIONS = {
    ("Gasabo", "51 46 21"): (51, 46, 2, 1),
    ("Nyarugenge", "59 40 1"): (59, 40, None, 1),   # informal-only segment unlabelled in Figure 13
    ("Urban 2024", "39 56 23"): (39, 56, 2, 3),
}


def pdf_text(path, pages: range | None = None) -> str:
    with pdfplumber.open(path) as pdf:
        sel = pdf.pages if pages is None else [pdf.pages[i - 1] for i in pages]
        return "\n".join((p.extract_text() or "") for p in sel)


def _strand(name: str, raw: str) -> tuple:
    vals = tuple(int(x) for x in raw.split())
    if len(vals) == 4:
        return vals
    key = (name, raw)
    if key in LABEL_RESOLUTIONS:
        return LABEL_RESOLUTIONS[key]
    raise ValueError(f"FinScope: cannot resolve labels for {name!r}: {raw!r}")


def _emit_strand(out, lvl, vals, period, table, resolved: bool):
    flags = ["merged_pdf_labels_resolved_visually"] if resolved else []
    for ind, v in zip(STRAND, vals):
        f = list(flags) + ([] if v is not None else ["unlabelled_segment_in_source_figure"])
        out.append(Obs(ind, *lvl, None if v is None else float(v), period, "finscope_2024", table,
                       status="official_transcribed", flags=f))
    present = [v for v in vals if v is not None]
    if vals[0] is not None and vals[1] is not None:
        out.append(Obs("fs_formally_served", *lvl, float(vals[0] + vals[1]), period, "finscope_2024",
                       f"Derived from {table}", status="calculated", flags=list(flags),
                       note="banked + other formal (non-bank)"))
    return sum(present)


FINSCOPE_HEADLINES = [
    # key, label, value, evidence string that must appear in the (whitespace-normalised) PDF text
    ("overall_inclusion", "Financially included (formal or informal)", 96, "96% financial inclusion rate"),
    ("formal_inclusion", "Formally included", 92, "formal inclusion at 92%"),
    ("accounts_in_own_name", "Adults with a financial product account in their own name", 86,
     "86% or 6.9 million of adult Rwandans had financial product accounts in their names"),
    ("mobile_money_account", "Mobile money account in own name", 77, "mobile money (77%)"),
    ("sacco_account", "Umurenge SACCO account in own name", 28, "SACCO (28%)"),
    ("insurance", "Insurance product in own name", 27, "insurance (27%)"),
    ("pension", "Pension product in own name", 25, "pension (25%)"),
    ("bank_account", "Bank product in own name", 22, "bank (22%)"),
    ("mfi", "Microfinance institution product in own name", 7, "MFI (7%)"),
    ("used_mobile_money", "Own or have used mobile money", 86, "86% (6.9 million) of Rwandans own or have used mobile money"),
]


def parse_finscope(path) -> tuple[list[Obs], list[dict]]:
    text = pdf_text(path)
    flat = " ".join(text.split())
    out: list[Obs] = []
    checks: list[dict] = []

    # Headlines from report text
    for key, label, value, evidence in FINSCOPE_HEADLINES:
        found = evidence in flat
        checks.append({"check": f"finscope_headline_evidence:{key}", "passed": found,
                       "detail": f"'{evidence}' {'found' if found else 'NOT found'} in PDF text"})
        if found:
            out.append(Obs("fs_headline", "national", "rwanda", "Rwanda", float(value), "2024", "finscope_2024",
                           "Report text", status="official_transcribed", breakdown=key, note=label))

    # Figure 5 national strand, Figure 6 area, Figure 7 sex (2024 and 2020)
    fig = text[text.rfind("Figure 5: Rwanda Financial Access Strand"):]
    m24 = re.search(r"^2024 (\d+(?: \d+)*)$", fig, re.M)
    m20 = re.search(r"^2020 (\d+(?: \d+)*)$", fig, re.M)
    for m, period in [(m24, "2024"), (m20, "2020")]:
        if not m:
            raise ValueError("FinScope Figure 5 not found")
        tot = _emit_strand(out, ("national", "rwanda", "Rwanda"), _strand("Rwanda", m.group(1)), period, "Figure 5", False)
        checks.append({"check": f"finscope_strand_sum:Rwanda:{period}", "passed": 98 <= tot <= 102, "detail": f"sum={tot}"})

    for label, lvl in [("Rural", ("area", "rural", "Rural")), ("Urban", ("area", "urban", "Urban")),
                       ("Male", ("sex", "male", "Male")), ("Female", ("sex", "female", "Female"))]:
        for period in ("2024", "2020"):
            m = re.search(rf"^{label} {period} (\d+(?: \d+)*)$", text, re.M)
            if not m:
                raise ValueError(f"FinScope: {label} {period} not found")
            vals = _strand(f"{label} {period}", m.group(1))
            resolved = (f"{label} {period}", m.group(1)) in LABEL_RESOLUTIONS
            tot = _emit_strand(out, lvl, vals, period, "Figure 6" if lvl[0] == "area" else "Figure 7", resolved)
            checks.append({"check": f"finscope_strand_sum:{label}:{period}",
                           "passed": 98 <= tot <= 102 or None in vals, "detail": f"sum={tot}"})

    # Figure 12 provinces
    f12 = text.rfind("Figure 12: Access Strand by Provinces")
    seg = text[f12:text.find("FAS by Districts", f12)]
    for key, pid in [("Kigali City", "kigali"), ("Southern", "southern"), ("Northern", "northern"),
                     ("Eastern", "eastern"), ("Western", "western")]:
        m = re.search(rf"{key}\D*?(\d+ \d+ \d+ \d+)", seg)
        if not m:
            raise ValueError(f"FinScope Figure 12: {key} not found")
        tot = _emit_strand(out, ("province", pid, PROVINCES[pid]), _strand(key, m.group(1)), "2024", "Figure 12", False)
        checks.append({"check": f"finscope_strand_sum:{pid}", "passed": 98 <= tot <= 102, "detail": f"sum={tot}"})

    # Figure 13 districts
    start = text.rfind("Figure 13: Financia")
    seg = text[start:text.find("Banked Other Formal", start)]
    for d in DISTRICT_PROVINCE:
        m = re.search(rf"{d}\s+(\d+(?: \d+)*)", seg)
        if not m:
            raise ValueError(f"FinScope Figure 13: {d} not found")
        raw = m.group(1)
        vals = _strand(d, raw)
        tot = _emit_strand(out, ("district", DISTRICT_IDS[d], d), vals, "2024", "Figure 13",
                           (d, raw) in LABEL_RESOLUTIONS)
        ok = 98 <= tot <= 102 or None in vals
        checks.append({"check": f"finscope_strand_sum:{d}", "passed": ok, "detail": f"sum={tot} raw='{raw}'"})
    return out, checks


# ----------------------------------------------------------------- Census 2022
def _int(s: str) -> int:
    return int(s.replace(",", ""))


def parse_census(path) -> tuple[list[Obs], list[dict]]:
    text = pdf_text(path)
    out: list[Obs] = []
    checks: list[dict] = []

    # Table 58 body (second occurrence; the first is the list of tables)
    t58 = [m.start() for m in re.finditer(r"Table 58: Private households \(Number\)", text)]
    if len(t58) < 2:
        raise ValueError("Census Table 58 body not found")
    seg = text[t58[1]: text.find("Source: Fifth Rwanda Population", t58[1])]
    rows = {}
    labels = ["Rwanda", *(["City of Kigali", "Southern Province", "Western Province", "Northern Province",
                           "Eastern Province"]), *DISTRICT_PROVINCE]
    for lab in labels:
        m = re.search(rf"^{lab} (\d{{1,3}}(?:,\d{{3}})+) (\d[\d,]*) (\d[\d,]*)", seg, re.M)
        if not m:
            raise ValueError(f"Census Table 58: row {lab} not found")
        total, urban, rural = (_int(x) for x in m.groups())
        rows[lab] = total
        checks.append({"check": f"census_t58_urban_plus_rural:{lab}", "passed": urban + rural == total,
                       "detail": f"{urban}+{rural} vs {total}"})
        lvl = canonical(lab)
        out.append(Obs("households_census", *lvl, float(total), "2022", "rphc5_main", "Table 58"))
    # districts sum to provinces, provinces to national
    for pid, pname in PROVINCES.items():
        ds = [d for d, p in DISTRICT_PROVINCE.items() if p == pid]
        s = sum(rows[d] for d in ds)
        checks.append({"check": f"census_t58_districts_sum_to_province:{pid}", "passed": s == rows[pname],
                       "detail": f"sum(districts)={s} vs province={rows[pname]}"})
    s = sum(rows[p] for p in PROVINCES.values())
    checks.append({"check": "census_t58_provinces_sum_to_national", "passed": s == rows["Rwanda"],
                   "detail": f"{s} vs {rows['Rwanda']}"})

    # Table 60 mean household size
    t60 = [m.start() for m in re.finditer(r"Table 60: Mean size of the private households", text)]
    seg = text[t60[1]: text.find("Table 61", t60[1])]
    for lab in labels:
        m = re.search(rf"^{lab} (\d+(?:\.\d+)?)\b", seg, re.M)
        if not m:
            raise ValueError(f"Census Table 60: row {lab} not found")
        out.append(Obs("household_size_census", *canonical(lab), float(m.group(1)), "2022", "rphc5_main", "Table 60"))
    return out, checks
