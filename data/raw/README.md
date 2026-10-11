# data/raw — original, unmodified source files

Files here are downloaded by `python -m backend.pipeline.build --fetch` (or `fetch.py`) from the
official URLs listed in `backend/pipeline/sources.py`. They are kept byte-for-byte unchanged and
their SHA-256 checksums and retrieval dates are recorded in `data/metadata/retrieval_log.json`.

They are not committed to Git because the publishers do not state redistribution terms.
Restricted microdata (e.g. EICV7 household files) are never placed here automatically — see
`docs/MICRODATA_IMPORT.md`.
