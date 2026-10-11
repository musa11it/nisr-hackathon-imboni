# Methodology

All values in Imboni come from official public tables. This document lists every transformation and formula.
Code references point to `backend/`.

## 1. Data model and status labels

Every value is one row in `data/processed/observations.csv`:
`indicator_id, level, geo_id, geo_name, value, period, source_id, table_ref, status, se, ci_low, ci_high, cv, deff, breakdown, flags, note`.

| Status | Meaning |
|---|---|
| `official` | Printed in an official NISR Excel table; reproduced unchanged (binary float noise rounded at 6 decimals). |
| `official_transcribed` | Official value extracted from a PDF's text layer (FinScope figures, Census tables). |
| `calculated` | Derived by Imboni from official values with a formula below. |
| `illustrative` | Depends on user/placeholder assumptions (simulator). |
| `experimental` | Imboni research method, not an official measure (service-gap index). |

Missing or suppressed values (`-` in a table, unlabelled chart segments) are stored as missing with a flag —
never as zero (`pipeline/model.py::num`).

## 2. Parsing

* **Excel** (`pipeline/parse_eicv.py`): rows are located by their printed labels; section headers
  ("Province", "District", "Quintile"…) set the geographic level. Geography names are canonicalised
  (`pipeline/geography.py`: e.g. "South" → Southern Province). A parser raises if an expected row is absent.
* **PDF** (`pipeline/parse_pdf.py`, pdfplumber text layer):
  * FinScope Figure 13 etc.: labels are parsed per district. Where the text layer merges two adjacent labels
    (e.g. Gasabo `51 46 21` = 51, 46, 2, 1) a resolution is applied only if the raw string matches exactly, and the
    figure was checked visually. Nyarugenge's informal-only segment is unlabelled in the figure → missing.
    Headline percentages are accepted only if an evidence sentence is found verbatim in the PDF text.
  * Census Table 58/60: regex on the table body; urban + rural = total and districts sum to provinces are checked.

## 3. Validation (`pipeline/validate.py`) — 189 checks

* **Benchmarks (17):** poverty 27.4%; MPI H 30.5% (urban 14.8, rural 36.7; 5 provinces); M0 0.136/0.065/0.164;
  A 44.6%; censored headcounts cooking fuel 29.2, housing 28.1, water 17.4, health insurance 15.1.
* **Identities:** M0 = H × A (|diff| ≤ 0.0015); Σ wⱼ·CHⱼ ≈ M0 (CH printed to 1 decimal); share-weighted provincial
  H ≈ national H; overlap cells sum to totals; overlap margins equal H and the poverty rate.
* **Structure:** no duplicates; all indicators catalogued; % in [0,100]; MPI in [0,1]; 30 districts / 5 provinces
  present where expected; CI contains the estimate and half-width ≈ 1.96·SE.
* **Cross-source:** EICV7 household estimate vs Census count within 5%; VUP payment channels sum to 100%;
  FinScope strands sum to 98–102%.

**Finding:** the MPI workbook's contribution tables (B.7–B.9) cannot be reproduced from Table B.2 and the official
weights (max gap 8.6–12.7 pp; e.g. cooking fuel printed 2.1% vs recomputed 10.6%). Imboni keeps both and uses the
recomputed (`calculated`) values in charts. Q1's Σ w·CH (0.260) also exceeds its printed M0 (0.253).

## 4. Official MPI framework (EICV7 MPI report, pp. 22–23)

Alkire–Foster dual cut-off; household = unit of identification; individual = unit of analysis; k = 1/3.

| Dimension (1/4 each) | Indicators (weight) |
|---|---|
| Education | School attendance (1/8), Years of schooling (1/8) |
| Health | Access to health care (1/8), Health insurance (1/8) |
| Basic services | Electricity, Drinking water, Sanitation, Cooking fuel, Garbage disposal (1/20 each) |
| Living standards | Housing materials, Assets, Overcrowding, Subsistence farming (1/16 each) |

Deprivation cut-offs are stored verbatim in `pipeline/indicators.py` and shown in the app. Imboni never computes
its own MPI; the experimental index (§8) is clearly separate.

## 5. Calculated indicators

| Name | Formula |
|---|---|
| Rural–urban MPI gap | H_rural − H_urban (pp); ratio H_rural / H_urban |
| Poor on either measure | both + MPI-only + monetary-only (Table 3.1 cells, % of population) |
| Share of monetary poor also MPI-poor | both / (both + monetary-only) |
| Poverty change | P₂₀₂₄ − P₂₀₁₇(modelled) and relative change (Poverty Profile Table 0.1/5.2) |
| Indicator contribution | wⱼ·CHⱼ / Σᵢ wᵢ·CHᵢ |
| Formally served (FinScope) | banked + other formal (non-bank) |
| Savings/MoMo gap | non-poor − poor (Poverty Profile Table 6.9) |

## 6. Uncertainty and comparisons (`app/analytics.py`)

* **CIs** are NISR's published 95% intervals; CV flags: > 15% "use with caution", > 30% "unreliable" (Imboni
  convention). CIs above 100% are flagged as normal-approximation artefacts.
* **Area vs national:** z = (x̂ − x̂ₙ)/√(SE² + SEₙ²), two-sided, α = 0.05. Approximate: ignores the positive
  covariance between a district and the national estimate (conservative) and is not multiplicity-adjusted —
  shown as screening signals.
* **Rank intervals:** 4,000 draws from independent Normal(x̂, SE) per area (seed 2026); the 5th–95th percentile of
  simulated ranks.
* **Correlations:** Spearman ρ across districts; 95% CI via Fisher z with SE = 1.06/√(n − 3); Benjamini–Hochberg
  FDR q-values. Ecological and descriptive only.
* **Not done (by design):** survey-weighted re-estimation, poverty-gap or inequality computation from microdata,
  and machine learning — these require authorised household microdata; 30 aggregate rows cannot support a
  defensible predictive model.

## 7. Budget simulator (`app/simulator.py`)

For target area *a* and intervention *j*:

```
amount_j   = budget × share_j                         (integer RWF, largest-remainder rounding:
                                                        Σ amount_j = round(budget × Σ share_j))
capacity_j = floor(amount_j / unit_cost_j)
eligible_j = households_a (Census 2022) × need_rate_j,a / 100
reached_j  = min(capacity_j, eligible_j)
idle_j     = amount_j − reached_j × unit_cost_j
coverage_j = reached_j / eligible_j
people_j   = reached_j × mean household size_a (Census 2022)
unallocated = budget − Σ amount_j
```

Need rates use the finest published level (district → province → national), flagged when a coarser level is
used. Need bases: no metal roof (A5.13), MPI-censored cooking fuel (B.3, province), no improved water (A5.16),
no electricity lighting (A5.14), no improved sanitation (A5.17), no health insurance (A3.7), FinScope excluded +
informal-only, MPI-censored school attendance. Person- or adult-based rates applied to households are labelled as
approximations. "Households reached" are household-interventions: unique households lie between the largest line
and the sum. Sensitivity recomputes reach with unit costs × 0.5, 0.8, 1, 1.2, 1.5. **Default unit costs are
placeholders**, not programme costings; outputs are illustrative and do not estimate poverty or MPI change.

The *need-weighted split* sets shares ∝ need rate — a transparent default, not an optimisation.

## 8. Experimental service-gap index

SGI_d = mean over j of z_dj, where x_dj is the share lacking service j (electricity, improved water, improved
sanitation, health insurance, metal roof, formal financial services) and z standardises across the 30 districts;
displayed 0–100 by min–max. Validation against district monetary poverty (not an input): Spearman ρ with CI;
leave-one-component-out rank correlations show sensitivity. Relative, equal-weighted, mixed universes — labelled
experimental throughout.

## 9. Natural-language explorer (`app/nlq.py`)

Keyword/synonym matching maps questions to indicators, geographies (in word order) and intents (value, compare,
rank, list, define). Answers are assembled only from stored observations, with source, period and caveats;
unmatched questions return suggestions. No language model is used.

## 10. Visual encoding

* Categorical series use the validated reference slots blue `#2a78d6`, orange `#eb6834`, aqua `#1baf7a` (and
  yellow `#eda100` only in adjacent stacks), checked with a colour-vision-deficiency validator; low-contrast slots
  always carry direct labels or table views.
* Choropleths use a single-hue teal ramp, quintile classes, darker = more deprived (inverted automatically for
  "higher is better" indicators); no-data areas are hatched; every map has a sortable table alternative and
  keyboard-focusable regions.
* No dual axes; status colours are reserved for status and always paired with icons/text.
