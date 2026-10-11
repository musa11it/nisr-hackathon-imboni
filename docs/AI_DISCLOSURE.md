# AI-assistance disclosure (draft for the DataMinds submission)

> The hackathon rules state: "AI tools may be used as assistants, but participants must disclose their use" and
> remain fully responsible for the work. **The team must review, edit and confirm this statement before submitting.**

**Tool used:** Claude (Anthropic), via Claude Code, as a coding assistant.

**What the AI assisted with**
- Inspecting the official NISR publications and Excel workbooks to identify available tables and variables.
- Drafting code: the data pipeline (download, parsing, validation), the FastAPI backend, the statistical
  functions, the budget simulator, the deterministic question-answering module, the React frontend and tests.
- Drafting documentation (README, methodology, data catalogue, deployment and demo guides).

**What the AI did not do**
- It did not generate, impute or invent any statistic. All figures come from the cited NISR/FinScope/Census
  publications via the reproducible pipeline; calculated values follow published formulas.
- The deployed application calls no external AI service and needs no AI API key.

**Human responsibility (to be completed by the team)**
- [ ] We reviewed the code and understand how each component works.
- [ ] We checked key figures against the original NISR publications.
- [ ] We reviewed the methodology, limitations and wording of findings.
- [ ] We ran the test suite and the application ourselves.
- Team members and roles: ______________________

**Declaration (hackathon requirement):** the work is original, has not been submitted to any other competition or
entity, and all sources are acknowledged (see `docs/DATA_SOURCES.md`).
