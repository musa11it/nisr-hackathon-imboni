# Importing authorised EICV7 microdata (workflow for approved users)

Imboni does **not** download microdata. The EICV7 cross-sectional files (NISR Microdata Portal, catalog 119,
`RWA-NISR-EICV7-2023-2024-v01`) require registration and acceptance of NISR's terms. Only users who have been
granted access should follow these steps, and only within the terms they accepted.

1. **Obtain access** at https://microdata.statistics.gov.rw/index.php/catalog/119 and download the files you are
   authorised to use.
2. **Store them outside Git**, e.g. `data/restricted/eicv7/` (add it to `.gitignore`; never commit or deploy
   household records).
3. **Identify design variables** from the DDI documentation (catalog 119 download 1084): household weight, strata
   and PSU/cluster identifiers, plus Section 10 credit/savings variables.
4. **Estimate with the survey design** (e.g. Python `samplics` or R `survey`): weighted proportions with
   Taylor-linearised SEs by district; suppress cells with too few observations or CV > 30%.
5. **Export aggregates only** to a CSV with the observation schema
   (`indicator_id, level, geo_id, geo_name, value, period, source_id, table_ref, status, se, ci_low, ci_high, cv, deff, breakdown, flags, note`),
   `status = calculated`, `source_id = eicv7_microdata`, and add the indicator definitions to
   `backend/pipeline/indicators.py`.
6. **Append in `build.py`** behind an explicit flag so public builds never require restricted files, rerun the
   validation and tests, and document the access licence in the source registry.

Never display household-level records, coordinates or any information that could identify respondents.
