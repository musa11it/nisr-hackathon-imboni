# Demo guide (≈ 7 minutes)

## Streamlit dashboard (primary)

**Setup:** `streamlit run streamlit_app.py` (or the Community Cloud URL once deployed), open full-screen.

| Time | Page | Show |
|---|---|---|
| 0:00 | **National Intelligence** | Monetary 27.4% (CI) vs MPI 30.5% — two concepts; overlap matrix: 14.3% poor on both, 43.6% on at least one. Hover a KPI ⓘ; point to Official/Calculated badges. |
| 1:00 | **Geographic Intelligence** | District poverty map + ranked bars with 95% CIs; hover Nyamagabe (rank interval). Switch indicator to MPI incidence → only Province is offered. *Area profile* → Nyamagabe fingerprint and significance findings. |
| 2:30 | **Multidimensional Poverty** | Censored vs uncensored headcounts; compare Rural/Urban/Q1; contributions: toggle Recomputed vs Published and explain the inconsistency found. |
| 3:30 | **Financial Inclusion** | Access strand 2020 vs 2024, districts map, poor vs non-poor savings, VUP channels, data-gap table. |
| 4:30 | **Intervention Simulator** | RWF 5,000 M → District → Nyamagabe → *Need-weighted split*; drag a slider past 100% (results withheld), *Equal split*, save, rename, change, save → comparison + CSV/PDF. Stress: illustrative arithmetic. |
| 5:45 | **Policy Insights** | Two cards: finding → statistics with badges → source → scope → implication (labelled interpretation) → limitations. |
| 6:30 | **Data Explorer / Sources & Methods** | Ask "Which districts have the highest poverty rate?"; data-quality tab; inventory of restricted datasets. |

## React + FastAPI variant

**Setup:** run the app (`uvicorn backend.app.main:app --port 8000` after `npm run build`), open
http://localhost:8000 full-screen. Pre-save two simulator scenarios for the comparison step.

| Time | Screen | Say / show |
|---|---|---|
| 0:00 | **Landing** | Track 2 challenge. "Two official lenses find different people": only 14.3% are poor on both; 43.6% are poor on at least one. Point to the Official/Calculated badges and "180/189 checks passed". |
| 0:50 | **Dashboard** | KPI cards: hover the ⓘ for definition, period, universe; click a source link. Stress that monetary poverty ≠ MPI incidence. Toggle censored/uncensored deprivations. |
| 1:50 | **Explorer** | District poverty map. Hover Nyamagabe (51.4%, CI 45.1–57.7, rank 1, interval 1–2). Switch to "Improved water": darker = more deprived (auto-inverted). Show the table view with CIs and rank intervals: "ranks 2–9 overlap — we don't over-claim". Switch to provinces → MPI is available only here. |
| 3:00 | **Profile → Nyamagabe** | Fingerprint dot plot vs Southern Province and Rwanda; "What stands out" uses significance tests. MPI panel shows the *province* with a warning that no district MPI exists. Download the PDF brief. |
| 4:00 | **Financial inclusion** | FinScope 30-district strand (transcribed, labelled). EICV7: 53% of poor vs 74% of non-poor households have a savings account. VUP payments mostly via SACCO; few on time. Scatter: ρ = −0.38 with CI touching 0 — "suggestive, ecological, not causal". Table of unavailable variables. |
| 5:00 | **Simulator** | Target Nyamagabe, RWF 5 bn, press "Need-weighted split". Show reconciliation (allocated + unallocated = budget), reach capped at need, need measured at province for cooking (flag), sensitivity table. Save; compare with a national scenario; export PDF. Repeat: illustrative, not a poverty forecast. |
| 6:00 | **Analysis** | Validation tab: benchmarks pass; the MPI contribution-table inconsistency we found. MPI deep-dive: k-sensitivity curve. Correlation matrix with FDR. |
| 6:40 | **Ask** | Click "How does rural MPI incidence compare with urban incidence?" → grounded answer with source and caveat. |
| 7:00 | **Close** | Impact: district planners and partners can target and cost interventions with honest uncertainty; next step is authorised microdata for survey-weighted district analysis. |

**Backup:** if the network is down everything still works locally — no external API calls at runtime.
