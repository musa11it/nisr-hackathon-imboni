# AI-assistance disclosure (draft for the DataMinds submission)

> The hackathon rules state: "AI tools may be used as assistants, but participants must disclose their use" and
> remain fully responsible for the work. **The team must review, edit and confirm this statement before submitting.**

**Tool used:** Claude (Anthropic), via Claude Code, as a coding assistant.

**What the AI assisted with**
- Inspecting the official NISR publications and Excel workbooks to identify available tables and variables.
- Drafting code: the data pipeline (download, parsing, validation), the FastAPI backend, the statistical
  functions, the budget simulator, the deterministic question-answering module, the React frontend and tests.
- Drafting documentation (README, methodology, data catalogue, deployment and demo guides).
- A second session (2026-10-30) assisted with: assessing the existing architecture; checking the accessibility of
  the official NISR source pages; the Streamlit dashboard (`streamlit_app.py`, `dashboard/`); the policy-insights
  module; the pipeline's data inventory, missing-source handling and data-quality summary; the GitHub Actions
  workflow; additional tests; and updates to the documentation.
- A UI/UX redesign of the Streamlit dashboard (2026-10-31): editorial page headers (with the geoBoundaries district
  outline as the graphic), KPI cards, key-finding cards computed from the data, sidebar styling, page layout,
  shorter on-page text (explanations moved into expandable notes) and a district poverty map on the National page.
  No statistic, calculation or data source was changed.

**What the AI did not do**
- It was not added as a Git author, co-author or repository collaborator.
- It did not generate, impute or invent any statistic. All figures come from the cited NISR/FinScope/Census
  publications via the reproducible pipeline; calculated values follow published formulas.
- The deployed application calls no external AI service and needs no AI API key.

**Human responsibility (to be completed by the team)**
- [ ] We reviewed the code and understand how each component works.
- [ ] We checked key figures against the original NISR publications.
- [ ] We reviewed the methodology, limitations and wording of findings.
- [ ] We reviewed and accept (or edited) the "potential implication" sentences in `backend/app/insights.py`, which
      were drafted with AI assistance and are labelled in the app as the team's interpretation.
- [ ] We ran the test suite and the application ourselves.
- Team members and roles: ______________________

**Declaration (hackathon requirement):** the work is original, has not been submitted to any other competition or
entity, and all sources are acknowledged (see `docs/DATA_SOURCES.md`).
