# Data source catalogue

The authoritative, machine-readable registry is `backend/pipeline/sources.py`; retrieval dates and SHA-256
checksums are in `data/metadata/retrieval_log.json` and shown on the in-app **Sources & methods** page.
All files were retrieved on **2026-10-11**.

| ID | Title / publisher | Period | Access | File | Variables used | Transformations |
|---|---|---|---|---|---|---|
| `eicv7_mi` | EICV7 Main Indicators Report — statistical tables, NISR | 2023/24 | Public download | `EICV7_Tables_MainIndicatorReport.xlsx` | Tables A9.23 (poverty, 30 districts), 9.2 (extreme poverty), A3.7, A5.12–A5.19, A6.20, A8.22, A1.3, 1.7, 8.1 | Label-based parsing; SE/CI/CV/deff kept; precision flags |
| `eicv7_mi_pdf` | EICV7 Main Indicators Report (PDF), NISR | 2023/24 | Public | `EICV7_Main_Indicator_Report.pdf` | Definitions | Reference only |
| `eicv7_mpi` | EICV7 MPI Thematic Report — tables, NISR | 2023/24 | Public | `Tables_and_Figures_EICV7_Multidimensional_Poverty_MPI.xlsx` | B.1–B.10, 3.1–3.3 | Parsing; contributions recomputed |
| `eicv7_mpi_pdf` | EICV7 MPI Thematic Report (PDF), NISR | 2023/24 | Public | `EICV7_Multidimensional_Poverty_Thematic_Report.pdf` | Framework, weights, cut-offs (pp. 22–23) | Transcribed into `indicators.py` |
| `eicv7_pp` | EICV7 Poverty Profile — tables, NISR | 2024 (+2017 modelled) | Public | `EICV7_Tables_Rwanda_Poverty_Profile.xlsx` | 0.1, 5.2, 5.3, 6.9, 6.11, 7.1 | Parsing; 2012 urban definition flagged |
| `eicv7_pp_pdf` | EICV7 Poverty Profile (PDF), NISR | 2024 | Public | `EICV7_Poverty_Profile.pdf` | Definitions | Reference only |
| `eicv7_vup` | EICV7 VUP Thematic Report — tables, NISR | 2023/24 | Public | `EICV7_VUP_Thematic_Report_Tables.xlsx` | 2.1, 2.2, 2.5, A.1, 4.2, 4.5, 4.8, 4.11, 4.13 | Parsing |
| `finscope_2024` | FinScope Rwanda 2024, AFR/NISR/BNR/MINECOFIN | 2024, adults 16+ | Public | `Rwanda_FinScope_2024_Report.pdf` | Figures 5, 6, 7, 12, 13; headline text | Text-layer extraction, evidence-checked; merged labels resolved & verified visually |
| `rphc5_main` | 5th Population & Housing Census — Main Indicators, NISR | Aug 2022 | Public | `RPHC5_MainIndicatorsReport_Final.pdf` | Tables 58, 60 | Regex extraction; totals checked |
| `eicv7_questionnaire` | EICV7 household questionnaire, NISR Microdata Portal | 2023/24 | Public documentation | `docs/EICV7_Questionnaire.pdf` | Sections 9–10 (savings, credit) | Used to establish which variables exist |
| `eicv7_method_note` | EICV7 Methodological Note, NISR | 2023/24 | Public | `docs/EICV7_Methodological_Note.pdf` | Design context | Reference |
| `eicv7_microdata` | EICV7 microdata, catalog 119 | 2023/24 | **Registration required — not accessed** | — | — | Import workflow documented |
| `eicv7_vup_microdata` | EICV7 VUP microdata, catalog 121 (`RWA-NISR-EICV7-VUP-2023-2024-V01`) | 2023/24 | **Registration required — not accessed** | — | — | Published VUP tables used instead |
| `nisr_gis` | NISR GIS portal, gis.statistics.gov.rw | — | Reference only (self-signed TLS certificate on 2026-10-30) | — | — | Not used; geoBoundaries used for maps |
| `geoboundaries_adm1/2` | geoBoundaries RWA ADM1/ADM2 (simplified), William & Mary geoLab | 2020 / 2012 boundaries | CC BY 4.0 | `boundaries/*.geojson` | Geometry | Coordinates rounded to 4 dp; names matched to EICV7 |

**Licence / terms.** NISR publications are public downloads; the download pages do not state an open licence, so
Imboni cites NISR and does not redistribute raw files in the repository (they are re-downloaded by the pipeline).
geoBoundaries data are CC BY 4.0. Photos are CC0 (see `frontend/public/images/CREDITS.md`).

**Citations** are listed per source in `sources.py` and in every PDF export.

## Source accessibility check (2026-10-30)

| Source page | Accessible | What it offers | Restrictions |
|---|---|---|---|
| [EICV7 Main Indicators](https://statistics.gov.rw/statistical-publications/poverty-and-social-protection/eicv7-main-indicators-report-202324) | Yes | Report PDF (updated 10 Jul 2025), tables XLSX (28 Apr 2025) | None stated; no open licence |
| [EICV7 Multidimensional Poverty](https://statistics.gov.rw/data-sources/surveys/EICV/integrated-household-living-conditions-survey-7-eicv-7/eicv7-thematic-report-multidimensional-poverty) | Yes | Report PDF (11 Jul 2025), tables XLSX (14 Jul 2025) | As above |
| [EICV7 Poverty Profile](https://statistics.gov.rw/data-sources/surveys/EICV/integrated-household-living-conditions-survey-7-eicv-7/eicv7-poverty-profile-report-202324) | Yes | Report PDF (10 Jul 2025), tables XLSX (19 May 2025) | As above |
| [EICV7 survey page](https://statistics.gov.rw/data-sources/surveys/EICV/integrated-household-living-conditions-survey-7-eicv-7) | Yes | 13 publications incl. VUP, education, youth, gender, utilities thematic reports, district PowerPoints | No financial-inclusion thematic report is listed |
| [EICV7 microdata (catalog 119)](https://microdata.statistics.gov.rw/index.php/catalog/119) | Landing page yes | Questionnaire, Kinyarwanda manual, methodological note, DDI metadata | Data files behind portal login/registration and the NISR Microdata Release Policy |
| [VUP microdata (catalog 121)](https://www.microdata.statistics.gov.rw/index.php/catalog/121) | Landing page yes | Questionnaire, VUP thematic report, DDI metadata | As catalog 119 |
| [NISR GIS](https://www.gis.statistics.gov.rw/) | Responds, but with a self-signed TLS certificate | Portal with download links | Not downloaded: certificate could not be verified, licence not stated |

## Data inventory and what still has to be obtained manually

`python -m backend.pipeline.inventory` writes `data/metadata/data_inventory.json` (shown on the dashboard's
**Sources & Methods** page). All required and optional public files were obtained and their checksums match the
retrieval log. Not obtained:

1. **EICV7 microdata (catalog 119)** — needed only for indicators NISR has not published (household credit, loan
   sources, savings depth, district-level savings/MoMo, design-based SEs for new breakdowns). *How:* register at
   https://microdata.statistics.gov.rw, read the Microdata Release Policy, open catalog 119 → **Get Microdata** and
   submit the request form describing the hackathon use; follow [MICRODATA_IMPORT.md](MICRODATA_IMPORT.md) if approved.
2. **EICV7 VUP microdata (catalog 121)** — same procedure; only needed for VUP analyses beyond the published tables.
3. **Official NISR boundary files** (optional) — from the NISR GIS portal or by request to NISR, if the team wants
   to replace geoBoundaries. Names must match the 30 EICV7 districts.

## Data dictionary

**Observation table** (`data/processed/observations.csv` / `.json`, one row per published or calculated value):

| Column | Meaning |
|---|---|
| `indicator_id` | Key into the indicator catalogue (`indicators.json`) |
| `level` | `national`, `area` (urban/rural), `province`, `district`, `quintile`, `sex`, `poverty_status`, `k_value`, `vup_component`, … |
| `geo_id`, `geo_name` | Stable identifier and display name within the level (e.g. `nyamagabe`, `q1`, `rural`) |
| `value` | The estimate (empty = missing, with a reason in `flags`; never zero-filled) |
| `period` | Reference period, e.g. `2023/24`, `2024`, `2020` |
| `source_id`, `table_ref` | Source registry id and the printed table/figure |
| `status` | `official`, `official_transcribed`, `calculated` (see METHODOLOGY §1) |
| `se`, `ci_low`, `ci_high`, `cv`, `deff` | Precision measures **as published by NISR** (empty when not published) |
| `breakdown` | Second dimension, e.g. overlap cell `mpi_poor__monetary_poor` or a shock response |
| `flags` | `;`-separated: `missing`, `suppressed_or_no_observations_in_source`, `cv_gt_15_use_with_caution`, `cv_gt_30_unreliable`, `ci_upper_above_100_normal_approx`, … |
| `note` | Free-text provenance note (e.g. the formula of a calculated value) |

**Indicator catalogue** (`indicators.json`): `id, name, short_name, theme, unit, universe, definition, source_id,
table_ref, polarity (higher_worse / higher_better / neutral), period, notes, status, decimals, levels`. Browse it
on the dashboard's **Data Explorer → Variables** tab.

**Data-quality summary** (`data_quality_summary.csv`): per indicator × level — `n_observations, n_present,
n_missing, pct_missing, missing_reasons, n_with_se, n_cv_gt_15, n_cv_gt_30, statuses`.

**Survey design (EICV7 Methodological Note, pp. 15–24, checked 2026-10-30).** The cross-sectional sample is a
stratified two-stage design: strata are district × urban/rural; primary sampling units are Census 2022
enumeration areas (clusters) selected with probability proportional to size from the Master Sample; 9 households
are selected per cluster by random systematic sampling; the basic household weight is the inverse of the overall
selection probability. The VUP sample is separate: strata by predominant VUP component, PSUs are clusters of VUP
beneficiaries (≥ 20 beneficiaries), 9 (later 12) households per cluster. Weights, strata and PSU identifiers exist
only in the restricted microdata. The published tables already embed NISR's weighting, and NISR publishes SEs, CVs
and design effects for many of them; Imboni uses those published precision measures and does not re-weight
anything.

## Benchmarks used only for validation

EICV7 monetary poverty 27.4%; MPI incidence 30.5% (rural 36.7%, urban 14.8%; Kigali 12.4%, Southern 35.2%,
Western 33.5%, Northern 28.7%, Eastern 34.4%); MPI 0.136 (urban 0.065, rural 0.164); censored headcounts —
cooking fuel 29.2%, housing materials 28.1%, drinking water 17.4%, health insurance 15.1%. All were verified
against the original tables by the pipeline.

## Notes on comparability

* Monetary poverty (consumption) and MPI incidence (deprivations) are different concepts.
* Poverty Profile Tables 5.1–5.2 use 2012 urban/rural definitions (urban poverty 12.7%); Main Indicators Table 9.1
  uses EICV7 definitions (urban 16.7%). Imboni never mixes them.
* 2017 poverty values are NISR's modelled re-estimates on the EICV7 methodology.
* FinScope (adults 16+, 2024) and EICV7 (households/population, 2023/24) differ in universe and period.
* FinScope states the registered-wallet count as both 5.8 million and 6.3 million in different places; Imboni uses
  only the percentage (77%).
* EICV7 Main Indicators Table 10.3 prints VUP flooring values as proportions (≈0.16) next to percentages; that table
  is not used.
