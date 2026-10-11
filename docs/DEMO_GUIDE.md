# Demo guide (≈ 7 minutes)

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
