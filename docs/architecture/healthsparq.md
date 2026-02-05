# Healthsparq Scraper Architecture

This document synthesizes how Ideon's Healthsparq-based scrapers operate, using `audiobee_capital_blue` as the reference implementation. Every Healthsparq project follows the same structure with plan-specific configuration.

---

## System Topology

- **Browser Automation Layer** – `healthsparq-server/` (Node.js + Puppeteer) exposes a local HTTP API that drives headless Chrome instances.  
  - Default port: `1018`, configurable per project via `PORT=<value> npm start`.
  - Uses stealth plugins, fingerprint injection, and optional VPN routing.
- **Python Scraper Layer** – Each `audiobee_*` Healthsparq project contains:
  - `config.py` describing plans, targeted states/counties, storage paths, and `HEALTHSPARK_PUPPETEER_PORT`.
  - Stage scripts (`index_1.py`, `index_2.py`, `index_3.py`) orchestrating search → detail → mapping.
  - `run_all.py` pipeline runner that sequentially executes the stage scripts, QA utilities, and housekeeping steps.
- **Shared Utilities**
  - [`healthspark_puppeteer`](https://git@bitbucket.org/productaudiobee/healthspark-puppeteer.git) Python package used by projects to submit tasks to `healthsparq-server`.
  - `output_generator/` (repository root) supplying QA helpers invoked at the end of each run (`type_checker`, `sample_generator`, `comparison_creator`, `report_generator`, etc.).

---

## Execution Flow

1. **Configuration Load**
   - Importing `config.py` materializes date-based directories (`CURR_DATE` / `PREV_DATE`, raw, processed, geocode cache).
   - Plan metadata (insurer, brand, product codes) and required states drive search permutations.
   - `HEALTHSPARK_PUPPETEER_PORT` locks the Python clients to the correct browser server port.

2. **Stage 1 – Search Coverage (`index_1.py`)**
   - Builds a counties/ZIP lookup from `uszips.xlsx` (full state coverage) and optional project-specific workbooks.
   - Invokes `healthspark.submit_task("get_search_response")` with dynamic filter combinations:
     - Baseline: provider type filters (`ORG_FILTERS`) and gender filters.
     - Expansion: specialty filters and language filters whenever result counts exceed thresholds (`>200`/`>400` results).
     - ZIP fallback: iterates ZIP codes per county when specialty expansion is required.
   - Saves every request/response map to `CURR_DATE/raw/search_results/<plan>/<state>_...json` including `_metadata.output_file_path`.
   - Logs exceptions and cardinality checks in `skipped.txt`.

3. **Stage 2 – Provider Detail Hydration (`index_2.py`)**
   - Deduplicates provider IDs from search payloads (cached in `provider_list_<plan>.json`).
   - Fetches detail via `healthspark.submit_task("get_provider_details")` and `"get_provider_details_v2"`; merges results and annotates with metadata.
   - Persists per-provider JSON under `CURR_DATE/raw/provider_details/` and batch-collated `provider_details_mapping_<product>_<batch>.json`.
   - `FileLock` guards prevent race conditions; skipped providers are appended to `skipped_providers.txt`.

4. **Stage 3 – Schema Mapping (`index_3.py`)**
   - Streams batched provider detail files, enriches with v1 location data, and maps into Ideon’s canonical JSON schema:
     - Normalizes provider demographics, NPIs, and network plan names.
     - Aggregates addresses with phone, language, PCP, and accepting-new-patient flags.
     - Collects group/hospital affiliations and specialties.
   - Writes results line-by-line to `CURR_DATE/processed/mapped_payload.jsonl`.

5. **QA + Packaging (`run_all.py`)**
   - After the three stages, `run_all.py` executes:
     - `compare_and_download_old_npi_4.py` (if present) for NPI diffs versus the previous run.
     - `generate_all_qa_files` block:
       - `type_checker` for schema validation.
       - `sample_generator` for spot-check files.
       - `comparison_creator` for run-to-run diffs.
       - `compress_folder_to_7z` to archive the processed folder.
       - `report_generator` to build Excel QA reports.
     - `get_per_STATE_counts.py` to reconcile total counts per state/plan.
     - `delete_extra_files` cleanup between stages.
   - Pipeline aborts on first failure, ensuring downstream tasks don’t consume partial outputs.

---

## Directory & File Conventions

```
<project>/
├── CURR_DATE/
│   ├── raw/
│   │   ├── search_results/
│   │   └── provider_details/
│   ├── processed/
│   │   ├── mapped_payload.jsonl
│   │   ├── type_check.json
│   │   ├── samples/
│   │   ├── comparisons/
│   │   └── reports/
│   └── <CURR_DATE>.7z
├── PREV_DATE/            # expected from prior run for QA comparisons
├── geocode_results/      # cached geocode lookups per location string
├── skipped.txt           # high-level search gaps
└── skipped_providers.txt # provider detail fetch errors
```

---

## Operational Runbook

1. **Prerequisites**
   - Node.js dependencies installed in `healthsparq-server/` (`npm install`).
   - Python env with dependencies listed in each project’s `pyproject.toml` (`uv pip install` or equivalent).
   - `output_generator/` package available on `PYTHONPATH` (repo root is added to `sys.path` in `run_all.py`).

2. **Launch Browser Server**
   ```bash
   cd healthsparq-server
   PORT=<project_port> npm start
   ```
   Keep the terminal open—Python processes communicate over `http://localhost:<port>`.

3. **Execute Project Pipeline**
   ```bash
   cd audiobee_<project>
   python3 run_all.py
   ```
   Monitor progress through the printed task list and emoji status markers.

4. **Post-Run Verification**
   - Confirm `mapped_payload.jsonl` exists and has non-zero line count.
   - Review `type_check.json` for failures.
   - Inspect generated sample files and comparison reports.
   - Address entries in `skipped*.txt` as required.

---

## Troubleshooting & Best Practices

- **Port mismatches** – Ensure `config.HEALTHSPARK_PUPPETEER_PORT` matches the port used when starting `healthsparq-server`. Each project typically reserves a unique port to avoid collision.
- **Large result sets** – `index_1.py` automatically pivots to specialty and language filters; if gaps remain, audit the `skipped.txt` logs and adjust thresholds.
- **Provider detail 404s** – Retries are built in via `tenacity`; persistent issues log to `skipped_providers.txt`. Manually validate the provider ID in Healthsparq UI if anomalies persist.
- **Memory pressure** – Batch writes (`provider_details_mapping_*.json`) limit in-memory payload size. If still constrained, reduce `MAX_WORKERS` or process states sequentially.
- **QA diffs** – `comparison_creator` output compares against `PREV_DATE` processed folder. Ensure prior data is available or skip the step when onboarding new projects.

---

## Related Documentation

- `audiobee_<project>/README.md` – Project-specific runbook (e.g., [audiobee_capital_blue/README.md](../../audiobee_capital_blue/README.md)).
- `healthsparq-server/CLAUDE.md` – Browser server architecture and API reference.
- `output-generator/CLAUDE.md` – QA tooling overview and maintenance notes.
- `/docs/by-site-type/healthsparq.md` – Catalog of Healthsparq projects with metadata.
- `/docs/site-type-mapping.md` – Cross-site type index.

---

By adhering to this architecture, new Healthsparq projects can be bootstrapped quickly—copy a reference project, update `config.py` (plans, states, port), and ensure `CLAUDE.md` reflects the correct run instructions and metadata.
