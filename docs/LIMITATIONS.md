# Known limitations and future improvements

## Limitations

1. **Aggregate tables only.** EICV7 microdata require registration and were not accessed, so Imboni cannot
   re-estimate indicators with survey weights, compute new disaggregations, poverty gaps by district, or
   household-level overlaps.
2. **No district MPI.** NISR publishes the MPI to province level. District profiles show the parent province's MPI
   for context only.
3. **Mixed universes and periods.** FinScope (adults 16+, 2024), EICV7 (households/population, 2023/24) and the
   Census (August 2022) are combined in profiles, correlations and the simulator; this is labelled but is a real
   limitation.
4. **Transcribed FinScope values.** District strands are rounded chart labels (sums 99–101%); one segment is unlabelled.
5. **Approximate significance tests** ignore covariance between a district and the national estimate and are not
   multiplicity-adjusted (correlations are FDR-adjusted).
6. **Simulator unit costs are placeholders.** Reach is arithmetic; the simulator does not model targeting
   efficiency, overlap between programmes, implementation capacity, or effects on poverty.
7. **Person- or adult-level rates applied to households** in some simulator need bases (labelled).
8. **Source inconsistencies** (MPI contribution tables, FinScope wallet counts, VUP Table 10.3 units) are documented,
   not resolved; NISR clarification would settle them.
9. **Persistence on free hosting** — SQLite in a container resets on redeploy unless a managed MySQL is configured.
10. **Deterministic Q&A** understands a limited vocabulary by design.

## Future improvements

* Authorised-microdata module: survey-weighted (Taylor-linearised) district estimates for savings, credit and MoMo
  (EICV7 Section 10), with design-based SEs; small-area estimation for district MPI with validation.
* Programme costing library from MINALOC/LODA/VUP budgets to replace placeholder unit costs.
* Panel/trend views as EICV8 and FinScope updates are released; automated checksum-change alerts already exist.
* Kinyarwanda interface; offline PDF district briefs for all 30 districts in one click.
* Alembic migrations and authenticated workspaces if multi-user scenario sharing is required.
