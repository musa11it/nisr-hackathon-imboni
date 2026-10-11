"""Indicator catalogue: definitions, units, universes and provenance.

``status`` vocabulary used across the app:
  official              – value printed in an official NISR Excel table
  official_transcribed  – official value transcribed from a figure/PDF (no Excel table exists)
  calculated            – derived by Imboni from official values (formula documented)
"""
from __future__ import annotations

from fractions import Fraction

EICV_PERIOD = "2023/24"

# --- Official Rwanda national MPI framework (EICV7 MPI Thematic Report, pp. 22-23) ---
MPI_INDICATORS = [
    # id, label, dimension, weight, deprivation cut-off (deprived if ...)
    ("school_attendance", "School attendance", "Education", Fraction(1, 8),
     "At least one school-aged child (6–11 years) in the household is not attending school."),
    ("years_of_schooling", "Years of schooling", "Education", Fraction(1, 8),
     "No household member aged 12+ has completed at least 6 years of schooling."),
    ("access_health_care", "Access to health care", "Health", Fraction(1, 8),
     "Household lives more than 3 km from a health facility (health post, health centre or district hospital)."),
    ("health_insurance", "Health insurance", "Health", Fraction(1, 8),
     "At least one household member has no health insurance."),
    ("electricity", "Electricity", "Basic services", Fraction(1, 20),
     "Household has no improved electricity (not connected to REG/other distributors and no solar panel system)."),
    ("drinking_water", "Drinking water", "Basic services", Fraction(1, 20),
     "No improved drinking-water source, or source more than 500 m away (rural) / 200 m (urban)."),
    ("sanitation", "Sanitation", "Basic services", Fraction(1, 20),
     "No improved sanitation (no flush toilet or pit latrine with slab)."),
    ("cooking_fuel", "Cooking fuel", "Basic services", Fraction(1, 20),
     "Household cooks with solid fuel (dung, wood, crop residue, shrubs or coal); charcoal is not counted as deprivation."),
    ("garbage_disposal", "Garbage disposal", "Basic services", Fraction(1, 20),
     "Garbage not disposed in a publicly managed refuse area, collection service, or own compost heap."),
    ("housing_materials", "Housing materials", "Living standards", Fraction(1, 16),
     "Inadequate (natural or rudimentary) material in any of floor, roof or walls."),
    ("assets", "Assets", "Living standards", Fraction(1, 16),
     "Household owns no more than one of: radio, TV, telephone, computer, bicycle, motorbike, refrigerator — and no car/truck."),
    ("overcrowding", "Overcrowding", "Living standards", Fraction(1, 16),
     "More than 3 household members per sleeping room."),
    ("subsistence_farming", "Subsistence farming", "Living standards", Fraction(1, 16),
     "Household is only engaged in subsistence agriculture and works as agricultural labourers."),
]
MPI_K = Fraction(1, 3)

# Labels as printed in the MPI workbook -> indicator id
MPI_LABELS = {
    "school attendance": "school_attendance",
    "years of schooling": "years_of_schooling",
    "access to health care": "access_health_care",
    "health insurance": "health_insurance",
    "electricity": "electricity",
    "drinking water": "drinking_water",
    "cooking fuel": "cooking_fuel",
    "garbage disposal": "garbage_disposal",
    "sanitation": "sanitation",
    "housing materials": "housing_materials",
    "assets": "assets",
    "overcrowding": "overcrowding",
    "subsistence farming": "subsistence_farming",
}


def _ind(id, name, theme, unit, universe, definition, source, table, polarity="neutral",
         period=EICV_PERIOD, short=None, notes=None, status="official", decimals=1):
    return dict(id=id, name=name, short_name=short or name, theme=theme, unit=unit,
                universe=universe, definition=definition, source_id=source, table_ref=table,
                polarity=polarity, period=period, notes=notes, status=status, decimals=decimals)


INDICATORS: list[dict] = [
    # ---------------- Monetary poverty ----------------
    _ind("poverty_rate", "Monetary poverty headcount rate", "monetary_poverty", "%", "Population",
         "Share of people living in households whose consumption per adult equivalent is below the national poverty line (EICV7, January 2024 prices).",
         "eicv7_mi", "Table A9.23 (also 9.1)", "higher_worse", short="Poverty rate",
         notes="Monetary poverty and MPI incidence are different concepts and must not be compared as if interchangeable."),
    _ind("extreme_poverty_rate", "Extreme poverty headcount rate", "monetary_poverty", "%", "Population",
         "Share of people whose consumption per adult equivalent is below the extreme (food) poverty line.",
         "eicv7_mi", "Table 9.2", "higher_worse", short="Extreme poverty"),
    _ind("poverty_rate_2017_modelled", "Poverty rate 2017 (modelled, comparable)", "monetary_poverty", "%", "Population",
         "EICV5 (2016/17) poverty rate re-estimated by NISR on the EICV7 methodology via an OLS consumption model with multiple imputation, so that 2017→2024 change is comparable.",
         "eicv7_pp", "Table 0.1 / 5.1 / 5.2", "higher_worse", period="2016/17 (modelled)", short="Poverty 2017 (modelled)",
         notes="Modelled baseline, not the originally published EICV5 rate."),
    _ind("poverty_rate_pp", "Poverty rate (Poverty Profile table, 1-decimal)", "monetary_poverty", "%", "Population",
         "Monetary poverty headcount as printed in the Poverty Profile tables (rounded). Urban/rural in Table 5.2 use the 2012 urban definition.",
         "eicv7_pp", "Table 0.1 / 5.2", "higher_worse", period="2024", short="Poverty (PP)",
         notes="Urban/rural rows here use the 2012 urban/rural definitions and differ from Table 9.1."),
    _ind("poverty_gap", "Poverty gap index", "monetary_poverty", "%", "Population",
         "Average shortfall of consumption below the poverty line, as a share of the line, averaged over the whole population (non-poor count as zero).",
         "eicv7_pp", "Table 5.2", "higher_worse", period="2024", short="Poverty gap",
         notes="Urban/rural use 2012 definitions."),
    _ind("poverty_gap_2017_modelled", "Poverty gap index 2017 (modelled)", "monetary_poverty", "%", "Population",
         "Poverty gap for 2016/17 re-estimated on the EICV7 methodology.", "eicv7_pp", "Table 5.2", "higher_worse",
         period="2016/17 (modelled)", short="Poverty gap 2017"),
    _ind("median_consumption_ae", "Median consumption per adult equivalent", "monetary_poverty", "RWF '000/yr", "Population",
         "Median annual consumption per adult equivalent, thousand RWF in January 2024 prices.",
         "eicv7_pp", "Table 5.3", "higher_better", period="2024", short="Median consumption", decimals=0),
    _ind("median_consumption_ae_2017", "Median consumption per adult equivalent, 2017", "monetary_poverty", "RWF '000/yr", "Population",
         "Median annual consumption per adult equivalent in 2016/17, thousand RWF in January 2024 prices.",
         "eicv7_pp", "Table 5.3", "higher_better", period="2016/17", short="Median consumption 2017", decimals=0),
    _ind("gini", "Gini coefficient of consumption", "monetary_poverty", "index (0–100)", "Population",
         "Inequality of consumption per adult equivalent (0 = perfect equality, 100 = maximal inequality).",
         "eicv7_pp", "Table 7.1", "higher_worse", period="2024", short="Gini"),
    _ind("theil_t", "Theil's T index", "monetary_poverty", "index", "Population",
         "General-entropy GE(1) inequality measure; decomposable into within- and between-group parts.",
         "eicv7_pp", "Table 7.1", "higher_worse", period="2024", short="Theil T"),

    # ---------------- Multidimensional poverty ----------------
    _ind("mpi_incidence", "MPI incidence (H)", "multidimensional_poverty", "%", "Population",
         "Share of people identified as multidimensionally poor: deprived in at least one third (k = 33.3%) of the weighted indicators of Rwanda's national MPI.",
         "eicv7_mpi", "Table B.5 / B.6", "higher_worse", short="MPI incidence"),
    _ind("mpi_intensity", "MPI intensity (A)", "multidimensional_poverty", "%", "MPI-poor population",
         "Average share of weighted deprivations experienced by multidimensionally poor people.",
         "eicv7_mpi", "Table B.5 / B.6", "higher_worse", short="MPI intensity"),
    _ind("mpi", "Multidimensional Poverty Index (M0 = H × A)", "multidimensional_poverty", "index (0–1)", "Population",
         "Adjusted headcount ratio M0 = H × A (Alkire–Foster), Rwanda national MPI, 13 indicators in 4 dimensions.",
         "eicv7_mpi", "Table B.5 / B.6", "higher_worse", short="MPI", decimals=3),
    _ind("population_share", "Population share", "demography", "%", "Population",
         "Share of national population living in the group, as reported alongside the MPI.",
         "eicv7_mpi", "Table B.5 / B.6", "neutral", short="Population share"),
    _ind("mpi_k_incidence", "MPI incidence at alternative poverty cut-off k", "multidimensional_poverty", "%", "Population",
         "Incidence H recomputed by NISR for poverty cut-offs k = 5%…100%.", "eicv7_mpi", "Table B.10", "higher_worse"),
    _ind("mpi_k_intensity", "MPI intensity at alternative k", "multidimensional_poverty", "%", "MPI-poor population",
         "Intensity A at poverty cut-offs k = 5%…100%.", "eicv7_mpi", "Table B.10", "higher_worse"),
    _ind("mpi_k_mpi", "MPI at alternative k", "multidimensional_poverty", "index (0–1)", "Population",
         "M0 at poverty cut-offs k = 5%…100%.", "eicv7_mpi", "Table B.10", "higher_worse", decimals=3),
    _ind("mpi_monetary_overlap", "MPI × monetary poverty overlap", "multidimensional_poverty", "% of national population", "Population",
         "Joint distribution of MPI status (k = 33.3%) and monetary status (national poverty line). Cells are shares of the national population.",
         "eicv7_mpi", "Tables 3.1–3.3", "neutral"),

    # ---------------- Household services (EICV7 annex, with precision) ----------------
    _ind("health_insurance_cov", "Health insurance coverage", "health", "%", "Population",
         "Share of the population with any health insurance (community-based Mutuelle, RAMA, MMI, private, etc.).",
         "eicv7_mi", "Table A3.7", "higher_better", short="Health insurance"),
    _ind("umudugudu", "Households living in planned rural settlement (umudugudu)", "housing", "%", "Households",
         "Share of households whose habitat is an umudugudu (planned grouped settlement).", "eicv7_mi", "Table A5.12",
         "neutral", short="Umudugudu"),
    _ind("roof_metal", "Metal / corrugated iron roofing", "housing", "%", "Households",
         "Share of households whose dwelling has metal/corrugated iron sheet roofing.", "eicv7_mi", "Table A5.13",
         "higher_better", short="Metal roof"),
    _ind("electricity_lighting", "Electricity as main lighting source", "basic_services", "%", "Households",
         "Share of households using electricity (grid or solar) as the main source of lighting.", "eicv7_mi", "Table A5.14",
         "higher_better", short="Electricity"),
    _ind("internet_home", "Internet access at home (incl. mobile)", "digital", "%", "Households",
         "Share of households with internet access at home, including through mobile phones.", "eicv7_mi", "Table A5.15",
         "higher_better", short="Internet at home"),
    _ind("improved_water", "Improved drinking-water source", "basic_services", "%", "Households",
         "Share of households using an improved drinking-water source (EICV definition; distance not applied).", "eicv7_mi", "Table A5.16",
         "higher_better", short="Improved water"),
    _ind("improved_sanitation", "Improved sanitation", "basic_services", "%", "Households",
         "Share of households using improved sanitation facilities.", "eicv7_mi", "Table A5.17", "higher_better",
         short="Improved sanitation"),
    _ind("mobile_phone", "Household owns a mobile phone", "digital", "%", "Households",
         "Share of households owning at least one mobile phone.", "eicv7_mi", "Table A5.18", "higher_better",
         short="Mobile phone"),
    _ind("smartphone", "Household owns a smartphone", "digital", "%", "Households",
         "Share of households owning at least one smartphone.", "eicv7_mi", "Table A5.19", "higher_better",
         short="Smartphone"),
    _ind("workforce_ratio", "Workforce-to-population ratio", "labour", "%", "Population of working age (EICV definition)",
         "Share of the working-age population that is in the workforce.", "eicv7_mi", "Table A6.20", "neutral",
         short="Workforce ratio"),
    _ind("sending_transfers", "Households sending transfers to another household", "transfers", "%", "Households",
         "Share of households that sent cash, food or in-kind transfers to another household in the last 12 months.",
         "eicv7_mi", "Table A8.22", "neutral", short="Sending transfers",
         notes="Measures inter-household support, not use of financial services."),
    _ind("sending_cash_transfers", "Households sending cash transfers", "transfers", "%", "Households",
         "Share of households that sent cash transfers to another household in the last 12 months.",
         "eicv7_mi", "Table 8.1", "neutral", short="Sending cash transfers",
         notes="Does not identify the channel (cash, mobile money or bank)."),
    _ind("avg_household_size", "Average household size (EICV7)", "demography", "persons", "Households",
         "Mean number of household members.", "eicv7_mi", "Table A1.3", "neutral", short="Household size", decimals=2),
    _ind("households_eicv", "Number of households (EICV7 estimate)", "demography", "thousand households", "Households",
         "Weighted estimate of households, thousands.", "eicv7_mi", "Table 1.7", "neutral", short="Households ('000)"),

    # ---------------- Census denominators ----------------
    _ind("households_census", "Private households (Census 2022)", "demography", "households", "Private households",
         "Number of private households enumerated in the Fifth Population and Housing Census (August 2022).",
         "rphc5_main", "Table 58", "neutral", period="2022", short="Households (Census)", decimals=0),
    _ind("household_size_census", "Mean private household size (Census 2022)", "demography", "persons", "Private households",
         "Mean size of private households, Census 2022.", "rphc5_main", "Table 60", "neutral", period="2022",
         short="HH size (Census)", decimals=1),

    # ---------------- Financial inclusion (official) ----------------
    _ind("hh_savings_account", "Household has at least one savings account", "financial_inclusion", "%", "Households",
         "Share of households in which at least one member has a savings account (EICV7, memo item in Poverty Profile Table 6.9).",
         "eicv7_pp", "Table 6.9 (memo)", "higher_better", period="2024", short="Savings account"),
    _ind("hh_momo_account", "Household has at least one mobile-money account", "financial_inclusion", "%", "Households",
         "Share of households with at least one MoMo / Mocash account (EICV7, memo item in Poverty Profile Table 6.9).",
         "eicv7_pp", "Table 6.9 (memo)", "higher_better", period="2024", short="MoMo account"),
    _ind("shock_response", "Main response to shocks", "resilience", "% of households reporting a shock", "Households reporting a shock",
         "Main way the household responded to its most severe shock.", "eicv7_pp", "Table 6.11", "neutral", period="2024"),
    _ind("fs_banked", "Adults banked (FinScope Access Strand)", "financial_inclusion", "%", "Adults 16+",
         "Share of adults using a product from a commercial bank (Access Strand: banked).",
         "finscope_2024", "Figures 5–7, 12, 13", "higher_better", period="2024", short="Banked",
         status="official_transcribed"),
    _ind("fs_other_formal", "Adults formally served, not banked", "financial_inclusion", "%", "Adults 16+",
         "Share of adults using non-bank formal products (mobile money, SACCO, MFI, insurance, pension) but not a bank.",
         "finscope_2024", "Figures 5–7, 12, 13", "neutral", period="2024", short="Other formal (non-bank)",
         status="official_transcribed"),
    _ind("fs_informal_only", "Adults informally served only", "financial_inclusion", "%", "Adults 16+",
         "Share of adults using only informal mechanisms (e.g. savings groups) and no formal product.",
         "finscope_2024", "Figures 5–7, 12, 13", "higher_worse", period="2024", short="Informal only",
         status="official_transcribed"),
    _ind("fs_excluded", "Adults financially excluded", "financial_inclusion", "%", "Adults 16+",
         "Share of adults using neither formal nor informal financial products/mechanisms.",
         "finscope_2024", "Figures 5–7, 12, 13", "higher_worse", period="2024", short="Excluded",
         status="official_transcribed"),
    _ind("fs_formally_served", "Adults formally served (banked + other formal)", "financial_inclusion", "%", "Adults 16+",
         "Banked + other formal (non-bank), computed from the transcribed Access Strand segments.",
         "finscope_2024", "Derived from Figures 12–13", "higher_better", period="2024", short="Formally served",
         status="calculated"),
    _ind("fs_headline", "FinScope 2024 headline indicators", "financial_inclusion", "%", "Adults 16+",
         "Headline percentages stated in the FinScope Rwanda 2024 report text.", "finscope_2024", "Report text pp. 25–27, 40",
         "neutral", period="2024", status="official_transcribed"),

    # ---------------- Social protection (VUP) ----------------
    _ind("vup_households", "Households in VUP programmes", "social_protection", "households", "Households",
         "Estimated number of households benefiting from VUP programmes.", "eicv7_vup", "Table 2.1", "neutral", decimals=0),
    _ind("vup_component_share", "Share of VUP households by component", "social_protection", "%", "VUP households",
         "Distribution of households benefiting from VUP by component (with standard errors).", "eicv7_vup", "Table 2.5", "neutral"),
    _ind("vup_component_households", "Households by VUP component", "social_protection", "households", "VUP households",
         "Estimated number of households participating in each VUP component.", "eicv7_vup", "Table 2.2", "neutral", decimals=0),
    _ind("vup_poverty_rate", "Poverty rate among VUP beneficiaries", "social_protection", "%", "Population in VUP households",
         "Monetary poverty rate among people in households benefiting from each VUP component.", "eicv7_vup", "Table A.1",
         "higher_worse"),
    _ind("vup_payment_sacco", "VUP payments received via Umurenge SACCO", "financial_inclusion", "%", "VUP beneficiaries",
         "Share of beneficiaries whose most recent payment was received through an Umurenge SACCO account.",
         "eicv7_vup", "Tables 4.2, 4.5, 4.8, 4.11", "neutral"),
    _ind("vup_payment_momo", "VUP payments received via mobile money", "financial_inclusion", "%", "VUP beneficiaries",
         "Share of beneficiaries whose most recent payment was received through MoMo/Airtel Money.",
         "eicv7_vup", "Tables 4.2, 4.5, 4.8, 4.11", "neutral"),
    _ind("vup_payment_on_time", "VUP last payment received on time", "social_protection", "%", "VUP beneficiaries",
         "Share of beneficiaries whose last payment arrived on time.", "eicv7_vup", "Tables 4.2, 4.5, 4.8, 4.11", "higher_better"),
    _ind("vup_fs_loan_approved", "VUP Financial Services loan approved", "financial_inclusion", "%", "FS participants",
         "Share of FS participants whose loan application was approved.", "eicv7_vup", "Table 4.13", "higher_better"),
    _ind("vup_fs_avg_loan", "Average VUP Financial Services loan", "financial_inclusion", "RWF", "FS participants",
         "Average loan amount received per individual from the VUP Financial Services component.", "eicv7_vup", "Table 4.13",
         "neutral", decimals=0),
]

for _id, _label, _dim, _w, _cut in MPI_INDICATORS:
    INDICATORS.append(_ind(
        f"mpi_ch_{_id}", f"Censored headcount — {_label}", "mpi_indicator", "%", "Population",
        f"Share of people who are multidimensionally poor AND deprived in {_label.lower()}. Deprived if: {_cut}",
        "eicv7_mpi", "Tables B.2–B.4", "higher_worse", short=_label))
    INDICATORS.append(_ind(
        f"mpi_uh_{_id}", f"Uncensored headcount — {_label}", "mpi_indicator", "%", "Population",
        f"Share of all people deprived in {_label.lower()}, regardless of MPI status. Deprived if: {_cut}",
        "eicv7_mpi", "Table B.1", "higher_worse", short=_label,
        notes="Table B.1 subtitle reads 'proportion of poor people', but the figure title and values describe all people (uncensored)."))
    INDICATORS.append(_ind(
        f"mpi_contrib_{_id}", f"Published contribution to MPI — {_label}", "mpi_indicator", "%", "Population",
        f"Percentage contribution of {_label.lower()} to M0 as printed in the MPI workbook.",
        "eicv7_mpi", "Tables B.7–B.9", "neutral", short=_label,
        notes="Cannot be reproduced from Table B.2 and the stated weights; see validation report."))
    INDICATORS.append(_ind(
        f"mpi_contrib_calc_{_id}", f"Recomputed contribution to MPI — {_label}", "mpi_indicator", "%", "Population",
        f"Contribution recomputed by Imboni as w_j × CH_j / Σ_i w_i × CH_i using official weights and censored headcounts.",
        "eicv7_mpi", "Derived from Tables B.2–B.4 + report weights", "neutral", short=_label, status="calculated"))

INDICATOR_INDEX = {i["id"]: i for i in INDICATORS}

# Variables EICV7 collects (questionnaire) but for which NISR publishes no aggregate table.
UNAVAILABLE_FINANCIAL = [
    {"variable": "Household borrowing / loan incidence", "where_collected": "EICV7 questionnaire, Section 10 Part A (Credit)",
     "status": "collected_not_published", "how_to_obtain": "Requires authorised EICV7 microdata (survey-weighted estimate)."},
    {"variable": "Loan source (bank, SACCO, MFI, relative, VSLA …)", "where_collected": "EICV7 Section 10 Part A",
     "status": "collected_not_published", "how_to_obtain": "Authorised microdata."},
    {"variable": "Loan purpose and repayment status", "where_collected": "EICV7 Section 10 Part A",
     "status": "collected_not_published", "how_to_obtain": "Authorised microdata."},
    {"variable": "Reasons loan applications were refused", "where_collected": "EICV7 Section 10 Part A",
     "status": "collected_not_published", "how_to_obtain": "Authorised microdata."},
    {"variable": "Savings amounts / savings channels for all households", "where_collected": "EICV7 Section 10 (Savings); Section 9 for VUP participants",
     "status": "collected_not_published", "how_to_obtain": "Authorised microdata."},
    {"variable": "Savings & MoMo account rates by district or province", "where_collected": "EICV7 (memo items in Poverty Profile Table 6.9 only by poverty status)",
     "status": "collected_not_published", "how_to_obtain": "Authorised microdata."},
    {"variable": "Bank account indicator in MPI", "where_collected": "Dropped from the EICV7 MPI (NISR: future EICV rounds will not capture it).",
     "status": "discontinued", "how_to_obtain": "Use FinScope for banking access."},
    {"variable": "Insurance (non-health) uptake by district", "where_collected": "FinScope 2024 reports national figures only in text/figures",
     "status": "not_available_subnational", "how_to_obtain": "FinScope microdata (NISR catalog 120) under its access terms."},
]
