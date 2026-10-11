"""Parsers for the official EICV7 Excel workbooks (Main Indicators, MPI, Poverty Profile, VUP).

Each parser locates rows by their printed labels (not by fixed row numbers) so a
re-issued workbook with shifted rows still parses, and raises if an expected
label is missing.
"""
from __future__ import annotations

import openpyxl

from .geography import canonical, norm
from .indicators import EICV_PERIOD, MPI_LABELS
from .model import Obs, num, precision_flags, slug


class ParseError(RuntimeError):
    pass


def load_rows(path, sheet: str) -> list[list]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    names = {n.strip(): n for n in wb.sheetnames}
    if sheet.strip() not in names:
        raise ParseError(f"{path.name}: sheet '{sheet}' not found")
    ws = wb[names[sheet.strip()]]
    rows = [[(c.strip() if isinstance(c, str) else c) for c in r] for r in ws.iter_rows(values_only=True)]
    wb.close()
    return rows


def _first_label(row: list) -> str:
    for c in row:
        if isinstance(c, str) and c.strip():
            return norm(c)
    return ""


def _is_source(label: str) -> bool:
    return label.lower().startswith(("source", "note"))


GROUP_LEVEL = {
    "area of residence": "area", "province": "province", "district": "district", "quintile": "quintile",
    "sex": "sex", "sex of household head": "sex_of_head", "sex of head": "sex_of_head",
}


def _level_for(group: str | None, label: str) -> tuple[str, str, str] | None:
    lab = norm(label)
    if group is None:
        c = canonical(lab)
        return c if c and c[0] == "national" else ("national", "rwanda", "Rwanda")
    lvl = GROUP_LEVEL.get(group.lower())
    if lvl in {"area", "province", "district"}:
        c = canonical(lab)
        if not c or c[0] != lvl:
            raise ParseError(f"Unrecognised {lvl} label '{lab}'")
        return c
    if lvl == "quintile":
        return ("quintile", lab.lower().replace(" ", ""), lab.upper())
    if lvl in {"sex", "sex_of_head"}:
        return (lvl, lab.lower(), lab.title())
    return (slug(group), slug(lab), lab)


def parse_se_table(path, sheet: str, indicator: str, source: str, *, period: str = EICV_PERIOD,
                   keep_levels: set[str] | None = None) -> list[Obs]:
    """Parse NISR's 'estimate, SE, CI low, CI high, CV, design effect' layout."""
    rows = load_rows(path, sheet)
    out: list[Obs] = []
    group = None
    for r in rows[2:]:
        label = norm(r[0]) if r and r[0] is not None else ""
        if not label:
            continue
        if _is_source(label):
            break
        vals = r[1:7]
        if all(v is None or (isinstance(v, str) and not v.strip()) for v in vals):
            group = label
            continue
        lvl = _level_for(group, label)
        if keep_levels and lvl[0] not in keep_levels:
            continue
        value, flags = num(vals[0])
        se, _ = num(vals[1]); lo, _ = num(vals[2]); hi, _ = num(vals[3]); cv, _ = num(vals[4]); deff, _ = num(vals[5])
        o = Obs(indicator, lvl[0], lvl[1], lvl[2], value, period, source, sheet.strip(),
                se=se, ci_low=lo, ci_high=hi, cv=cv, deff=deff, flags=list(flags))
        precision_flags(o)
        out.append(o)
    if not any(o.level == "national" for o in out):
        raise ParseError(f"{sheet}: no national row found")
    return out


def _find_header(rows: list[list], wanted: list[str]) -> tuple[int, dict[str, int]]:
    """Find the row containing the wanted column labels; return (row_index, label->col)."""
    want = {w.lower(): w for w in wanted}
    for i, r in enumerate(rows):
        cols = {}
        for j, c in enumerate(r):
            if isinstance(c, str) and norm(c).lower() in want:
                cols[want[norm(c).lower()]] = j
        if len(cols) == len(wanted):
            return i, cols
    raise ParseError(f"Header {wanted} not found")


# ---------------------------------------------------------------- MPI workbook
def parse_mpi(path) -> list[Obs]:
    src = "eicv7_mpi"
    out: list[Obs] = []

    def indicator_rows(rows, start):
        for r in rows[start + 1:]:
            for c in r:
                if isinstance(c, str) and norm(c).lower() in MPI_LABELS:
                    yield MPI_LABELS[norm(c).lower()], r
                    break

    # B.1 uncensored (national)
    rows = load_rows(path, "Table B.1")
    hi, cols = _find_header(rows, ["Indicator", "EICV7"])
    seen = set()
    for ind, r in indicator_rows(rows, hi):
        v, f = num(r[cols["EICV7"]])
        out.append(Obs(f"mpi_uh_{ind}", "national", "rwanda", "Rwanda", v, EICV_PERIOD, src, "Table B.1", flags=f))
        seen.add(ind)
    if len(seen) != 13:
        raise ParseError(f"Table B.1: expected 13 indicators, got {len(seen)}")

    def matrix(sheet, prefix, columns: dict[str, tuple[str, str, str]]):
        rows = load_rows(path, sheet)
        hi, cols = _find_header(rows, list(columns))
        n = 0
        for ind, r in indicator_rows(rows, hi):
            for label, (lvl, gid, gname) in columns.items():
                v, f = num(r[cols[label]])
                out.append(Obs(f"{prefix}{ind}", lvl, gid, gname, v, EICV_PERIOD, src, sheet, flags=f))
            n += 1
        if n != 13:
            raise ParseError(f"{sheet}: expected 13 indicator rows, got {n}")

    area_cols = {"Urban": ("area", "urban", "Urban"), "Rural": ("area", "rural", "Rural"),
                 "National": ("national", "rwanda", "Rwanda")}
    prov_cols = {lab: canonical(lab) for lab in ["City of Kigali", "Southern", "Western", "Northern", "Eastern"]}
    q_cols = {f"Q{i}": ("quintile", f"q{i}", f"Q{i}") for i in range(1, 6)}

    matrix("Table B.2", "mpi_ch_", area_cols)
    matrix("Table B.3", "mpi_ch_", prov_cols)
    matrix("Table B.4", "mpi_ch_", q_cols)
    matrix("Table B.7", "mpi_contrib_", area_cols)
    matrix("Table B.8", "mpi_contrib_", prov_cols)
    matrix("Table B.9", "mpi_contrib_", q_cols)

    # B.5 / B.6 : population share, H, A, M0
    for sheet in ("Table B.5", "Table B.6"):
        rows = load_rows(path, sheet)
        hi, cols = _find_header(rows, ["Pop. Share", "Incidence (H), %", "Intensity (A); %", "MPI (M0)"])
        for r in rows[hi + 1:]:
            label = _first_label(r)
            if not label or _is_source(label):
                continue
            if label.upper().startswith("Q") and label[1:].isdigit():
                lvl = ("quintile", label.lower(), label.upper())
            else:
                lvl = canonical(label)
                if lvl is None:
                    raise ParseError(f"{sheet}: unknown row '{label}'")
            for ind, col in [("population_share", "Pop. Share"), ("mpi_incidence", "Incidence (H), %"),
                             ("mpi_intensity", "Intensity (A); %"), ("mpi", "MPI (M0)")]:
                v, f = num(r[cols[col]])
                out.append(Obs(ind, *lvl, v, EICV_PERIOD, src, sheet, flags=f))

    # B.10 : k sensitivity
    rows = load_rows(path, "Table B.10")
    hi, cols = _find_header(rows, ["k-value", "Incidence (H)", "Intensity (A)", "MPI"])
    for r in rows[hi + 1:]:
        k, _ = num(r[cols["k-value"]])
        if k is None:
            continue
        for ind, col in [("mpi_k_incidence", "Incidence (H)"), ("mpi_k_intensity", "Intensity (A)"), ("mpi_k_mpi", "MPI")]:
            v, f = num(r[cols[col]])
            out.append(Obs(ind, "k_value", f"k{int(k)}", f"k = {int(k)}%", v, EICV_PERIOD, src, "Table B.10", flags=f))

    # 3.1 - 3.3 : MPI x monetary overlap (shares of national population)
    def overlap_block(rows, start, lvl):
        cells = {}
        for r in rows[start:start + 9]:
            labels = [norm(c) for c in r if isinstance(c, str)]
            nums = [c for c in r if isinstance(c, (int, float))]
            row_key = next((l for l in ("Non-poor", "Poor", "Total") if l in labels), None)
            if row_key and len(nums) == 3:
                for col_key, v in zip(("monetary_nonpoor", "monetary_poor", "total"), nums):
                    cells[(row_key, col_key)] = float(v)
                if row_key == "Total":
                    break
        mapping = {("Non-poor", "monetary_nonpoor"): "mpi_nonpoor__monetary_nonpoor",
                   ("Non-poor", "monetary_poor"): "mpi_nonpoor__monetary_poor",
                   ("Non-poor", "total"): "mpi_nonpoor__total",
                   ("Poor", "monetary_nonpoor"): "mpi_poor__monetary_nonpoor",
                   ("Poor", "monetary_poor"): "mpi_poor__monetary_poor",
                   ("Poor", "total"): "mpi_poor__total",
                   ("Total", "monetary_nonpoor"): "total__monetary_nonpoor",
                   ("Total", "monetary_poor"): "total__monetary_poor",
                   ("Total", "total"): "total__total"}
        if len(cells) != 9:
            raise ParseError(f"Overlap block for {lvl[2]}: found {len(cells)} cells")
        for key, cell in mapping.items():
            out.append(Obs("mpi_monetary_overlap", *lvl, cells[key], EICV_PERIOD, src,
                           "Tables 3.1–3.3", breakdown=cell))

    rows = load_rows(path, "Table 3.1")
    overlap_block(rows, 0, ("national", "rwanda", "Rwanda"))
    for sheet, names in [("Table 3.2", ["Urban", "Rural"]),
                         ("Table 3.3", ["City of Kigali", "Southern", "Western", "Northern", "Eastern"])]:
        rows = load_rows(path, sheet)
        for i, r in enumerate(rows):
            lab = _first_label(r)
            if lab in names and not any(isinstance(c, (int, float)) for c in r):
                overlap_block(rows, i + 1, canonical(lab))
    return out


# ------------------------------------------------------- Main Indicators workbook
MI_SE_TABLES = [
    ("Table A9.23", "poverty_rate"),
    ("Table A3.7", "health_insurance_cov"),
    ("Table A5.12", "umudugudu"),
    ("Table A5.13", "roof_metal"),
    ("Table A5.14", "electricity_lighting"),
    ("Table A5.15", "internet_home"),
    ("Table A5.16", "improved_water"),
    ("Table A5.17", "improved_sanitation"),
    ("Table A5.18", "mobile_phone"),
    ("Table A5.19", "smartphone"),
    ("Table A6.20", "workforce_ratio"),
    ("Table A8.22", "sending_transfers"),
    ("Table A1.3", "avg_household_size"),
]


def parse_main_indicators(path) -> list[Obs]:
    src = "eicv7_mi"
    out: list[Obs] = []
    for sheet, ind in MI_SE_TABLES:
        out += parse_se_table(path, sheet, ind, src)

    # 9.2 extreme poverty (no group headers; rows are national/area/province)
    rows = load_rows(path, "Table 9.2")
    for r in rows[2:]:
        lab = _first_label(r)
        if not lab or _is_source(lab):
            continue
        lvl = canonical(lab)
        if not lvl:
            raise ParseError(f"Table 9.2: unknown row {lab}")
        v, f = num(r[1]); se, _ = num(r[2]); lo, _ = num(r[3]); hi, _ = num(r[4]); cv, _ = num(r[5]); de, _ = num(r[6])
        o = Obs("extreme_poverty_rate", *lvl, v, EICV_PERIOD, src, "Table 9.2", se=se, ci_low=lo, ci_high=hi, cv=cv, deff=de, flags=f)
        precision_flags(o)
        out.append(o)

    # 1.7 households (000s) and 8.1 cash transfers
    for sheet, ind, col in [("Table 1.7", "households_eicv", 2), ("Table 8.1", "sending_cash_transfers", 2)]:
        rows = load_rows(path, sheet)
        for r in rows[2:]:
            lab = _first_label(r)
            if not lab or _is_source(lab):
                continue
            lvl = canonical(lab)
            if lvl is None:
                if lab.upper() in {f"Q{i}" for i in range(1, 6)}:
                    lvl = ("quintile", lab.lower(), lab.upper())
                elif lab.lower() in {"male", "female"}:
                    lvl = ("sex_of_head", lab.lower(), lab.title())
                else:
                    continue  # group header rows
            v, f = num(r[col])
            if v is None and "missing" in f:
                continue
            out.append(Obs(ind, *lvl, v, EICV_PERIOD, src, sheet, flags=f))
    return out


# ------------------------------------------------------ Poverty Profile workbook
def parse_poverty_profile(path) -> list[Obs]:
    src = "eicv7_pp"
    out: list[Obs] = []

    # Table 0.1: provinces + national, 2024 actual and 2017 modelled, with 2024 CI
    rows = load_rows(path, "Table 0.1.")
    for r in rows:
        lab = _first_label(r)
        lvl = canonical(lab) if lab else None
        if not lvl or lvl[0] not in {"province", "national"}:
            continue
        v24, f24 = num(r[1]); v17, f17 = num(r[2]); lo, _ = num(r[5]); hi, _ = num(r[6])
        out.append(Obs("poverty_rate_pp", *lvl, v24, "2024", src, "Table 0.1", ci_low=lo, ci_high=hi, flags=f24))
        out.append(Obs("poverty_rate_2017_modelled", *lvl, v17, "2016/17 (modelled)", src, "Table 0.1", flags=f17))

    # Table 5.2: headcount & poverty gap, urban/rural (2012 def) + national
    rows = load_rows(path, "Table 5.2.")
    block = "headcount"
    for r in rows:
        lab = _first_label(r)
        if lab.lower().startswith("% poverty gap"):
            block = "gap"
        lvl = canonical(lab) if lab else None
        if not lvl or lvl[0] not in {"area", "national"}:
            continue
        v24, f24 = num(r[1]); v17, f17 = num(r[2])
        note = "Urban/rural defined with 2012 definitions." if lvl[0] == "area" else None
        if block == "headcount":
            if lvl[0] == "area":
                out.append(Obs("poverty_rate_pp", *lvl, v24, "2024", src, "Table 5.2", flags=f24 + ["urban_rural_2012_definition"], note=note))
                out.append(Obs("poverty_rate_2017_modelled", *lvl, v17, "2016/17 (modelled)", src, "Table 5.2", flags=f17 + ["urban_rural_2012_definition"], note=note))
        else:
            extra = ["urban_rural_2012_definition"] if lvl[0] == "area" else []
            out.append(Obs("poverty_gap", *lvl, v24, "2024", src, "Table 5.2", flags=f24 + extra, note=note))
            out.append(Obs("poverty_gap_2017_modelled", *lvl, v17, "2016/17 (modelled)", src, "Table 5.2", flags=f17 + extra, note=note))

    # Table 5.3 median consumption (thousand RWF, Jan 2024 prices)
    rows = load_rows(path, "Table 5.3.")
    for r in rows:
        lab = _first_label(r)
        if not lab:
            continue
        key = lab.split(":")[0].strip()
        lvl = canonical(key)
        if lvl is None and key.upper() in {f"Q{i}" for i in range(1, 6)}:
            lvl = ("quintile", key.lower(), key.upper())
        if not lvl:
            continue
        v24, f24 = num(r[1]); v17, f17 = num(r[2])
        out.append(Obs("median_consumption_ae", *lvl, v24, "2024", src, "Table 5.3", flags=f24))
        out.append(Obs("median_consumption_ae_2017", *lvl, v17, "2016/17", src, "Table 5.3", flags=f17))

    # Table 7.1 inequality
    rows = load_rows(path, "Table 7.1.")
    for r in rows:
        lab = _first_label(r)
        if lab == "Estimate":
            lvl = ("national", "rwanda", "Rwanda")
        else:
            lvl = canonical(lab) if lab else None
            if not lvl or lvl[0] not in {"area", "province"}:
                continue
        g, fg = num(r[1]); t, ft = num(r[2])
        ci = None
        if lab == "Estimate":
            nxt = rows[rows.index(r) + 1]
            if isinstance(nxt[1], str) and "-" in nxt[1]:
                lo, hi = (float(x) for x in nxt[1].split("-"))
                ci = (lo, hi)
        out.append(Obs("gini", *lvl, g, "2024", src, "Table 7.1", ci_low=ci[0] if ci else None,
                       ci_high=ci[1] if ci else None, flags=fg))
        out.append(Obs("theil_t", *lvl, t, "2024", src, "Table 7.1", flags=ft))

    # Table 6.9 memo items: savings account, MoMo account by poverty status
    rows = load_rows(path, "Table 6.9.")
    hi_, cols = _find_header(rows, ["Non-poor", "Poor", "All"])
    for r in rows[hi_ + 1:]:
        lab = _first_label(r).lower()
        ind = "hh_savings_account" if "savings account" in lab else "hh_momo_account" if "momo" in lab else None
        if not ind:
            continue
        for col, lvl in [("Non-poor", ("poverty_status", "non_poor", "Non-poor")),
                         ("Poor", ("poverty_status", "poor", "Poor")),
                         ("All", ("national", "rwanda", "Rwanda"))]:
            v, f = num(r[cols[col]])
            out.append(Obs(ind, *lvl, v, "2024", src, "Table 6.9 (memo)", flags=f))

    # Table 6.11 responses to shocks
    rows = load_rows(path, "Table 6.11.")
    hi_, cols = _find_header(rows, ["Non-poor", "Poor", "All"])
    for r in rows[hi_ + 1:]:
        lab = _first_label(r)
        if not lab or _is_source(lab) or lab.lower() in {"total"} or lab.startswith(("Main way", "Any form", "%")):
            continue
        for col, lvl in [("Non-poor", ("poverty_status", "non_poor", "Non-poor")),
                         ("Poor", ("poverty_status", "poor", "Poor")),
                         ("All", ("national", "rwanda", "Rwanda"))]:
            v, f = num(r[cols[col]])
            out.append(Obs("shock_response", *lvl, v, "2024", src, "Table 6.11", breakdown=lab, flags=f))
    return out


# ------------------------------------------------------------- VUP workbook
VUP_COMPONENTS = {
    "direct support": "Direct Support", "classic public work": "Classic Public Works",
    "classic public works": "Classic Public Works", "expanded public work": "Expanded Public Works",
    "expended public works": "Expanded Public Works", "nsds": "NSDS",
    "nutrition-sensitive direct support": "NSDS", "financial services": "Financial Services",
    "asset transfers": "Asset Transfers", "skills development": "Skills Development",
    "all vup components": "All VUP",
}


def _component(label: str) -> tuple[str, str, str] | None:
    name = VUP_COMPONENTS.get(norm(label).lower())
    if not name:
        return None
    return ("vup_component" if name != "All VUP" else "vup_all", slug(name), name)


def parse_vup(path) -> list[Obs]:
    src = "eicv7_vup"
    out: list[Obs] = []

    rows = load_rows(path, "Table 2.1")
    for r in rows:
        lab = _first_label(r)
        lvl = canonical(lab) if lab else None
        nums = [c for c in r if isinstance(c, (int, float))]
        if lvl and len(nums) == 4:
            out.append(Obs("vup_households", *lvl, float(nums[3]), EICV_PERIOD, src, "Table 2.1"))

    rows = load_rows(path, "Table 2.2")
    for r in rows:
        comp = _component(_first_label(r))
        nums = [c for c in r if isinstance(c, (int, float))]
        if comp and len(nums) == 4:
            out.append(Obs("vup_component_households", *comp, float(nums[3]), EICV_PERIOD, src, "Table 2.2"))

    for sheet, ind in [("Table 2.5", "vup_component_share"), ("Table_A.1", "vup_poverty_rate")]:
        rows = load_rows(path, sheet)
        for r in rows:
            comp = _component(_first_label(r))
            nums = [c for c in r if isinstance(c, (int, float))]
            if comp and len(nums) == 5:
                o = Obs(ind, *comp, float(nums[0]), EICV_PERIOD, src, sheet, se=float(nums[1]),
                        ci_low=float(nums[2]), ci_high=float(nums[3]), cv=float(nums[4]))
                precision_flags(o)
                out.append(o)

    # Payment channel & timeliness by component (Total column)
    for sheet, comp_name in [("Table 4.2", "Direct Support"), ("Table 4.5", "Classic Public Works"),
                             ("Table 4.8", "Expanded Public Works"), ("Table 4.11", "NSDS")]:
        rows = load_rows(path, sheet)
        hi_, cols = _find_header(rows, ["Total"])
        comp = ("vup_component", slug(comp_name), comp_name)
        found = set()
        for r in rows[hi_ + 1:]:
            lab = _first_label(r).lower()
            ind = ("vup_payment_sacco" if lab == "umurenge sacco" else
                   "vup_payment_momo" if lab.startswith("momo") else
                   "vup_payment_on_time" if lab in {"paid on time", "on time"} else None)
            if ind and ind not in found:
                v, f = num(r[cols["Total"]])
                out.append(Obs(ind, *comp, v, EICV_PERIOD, src, sheet, flags=f))
                found.add(ind)
        if len(found) != 3:
            raise ParseError(f"{sheet}: expected payment channel + timeliness rows, found {found}")

    rows = load_rows(path, "Table 4.13")
    hi_, cols = _find_header(rows, ["Total"])
    comp = ("vup_component", "financial_services", "Financial Services")
    block = None
    for r in rows[hi_ + 1:]:
        lab = _first_label(r)
        if lab.lower().startswith("loan approval"):
            block = "approval"
        if block == "approval" and lab == "Approved":
            v, f = num(r[cols["Total"]])
            out.append(Obs("vup_fs_loan_approved", *comp, v, EICV_PERIOD, src, "Table 4.13", flags=f))
            block = None
        if lab.lower() == "average loan amount received":
            v, f = num(r[cols["Total"]])
            out.append(Obs("vup_fs_avg_loan", *comp, v, EICV_PERIOD, src, "Table 4.13", flags=f))
    return out
