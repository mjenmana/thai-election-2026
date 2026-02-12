# Thai Election 2026: ECT Google Drive Mirror + OCR Pipeline

This repository helps:

1. **Mirror the Election Commission of Thailand (ECT) Google Drive folders** (keeping their original structure), while letting you **select only specific provinces** to download.
2. **Digitise PDF vote-result forms** into machine-readable text using the **Typhoon OCR** API.

The project is designed so that collaborators can “claim” provinces, run the pipeline locally, and share back outputs.

---

## What’s in this repo

### Key folders

- `configs/`
  - `province_links.csv` — mapping of province → Google Drive folder link (or folder ID)
  - `provinces.txt` — list of provinces you want to operate on (one per line, Thai spelling must match the CSV)
  - `ocr.yaml` — OCR configuration (model, rate limits, etc.)
- `scripts/`
  - `sync_selected_from_csv.sh` — download selected provinces (preserve structure)
  - `index_remote_snapshot.sh` — build a remote snapshot index (all provinces)
  - `index_one_province.py` — helper used by snapshot indexer
  - `make_remote_index_summary.py` — generates readable summaries from the snapshot status file
  - `run_typhoon_ocr.py` — OCR runner (uses Typhoon API)
- `data/remote_index/published/` (**committed, public**)
  - `summary.md` — **human-readable latest snapshot** (start here)
  - `summary.csv` — same info in CSV form
  - `status.jsonl` — per-province status rollup (JSONL)
  - `items.jsonl.gz` — full remote listing (compressed JSONL)
  - `README.md` — how to use the snapshot files
- `data/raw/` (NOT committed) — downloaded Google Drive files (your local mirror)
- `data/ocr/` (NOT committed by default) — OCR outputs (your local)

> The repo intentionally does **not** commit the raw mirrored PDFs (too large).  
> Only the **remote index snapshot** is committed so everyone can see what ECT has uploaded so far.

---

## Quickstart (macOS)

### 0) Prerequisites

Install these once:

- Git
- Python 3.10+ (recommended via `pyenv` or system python)
- `rclone` (for Google Drive mirroring)

Homebrew:
brew install rclone

### 1) Clone the repo

    git clone https://github.com/mjenmana/thai-election-2026.git
    cd thai-election-2026

### 2) Create a Python virtual environment

    python -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install -r requirements.txt

---

## Latest ECT upload status (remote snapshot)

Before downloading anything, check what exists on the ECT drives **right now**:

- Open: `data/remote_index/published/summary.md`

That file shows, for each province:

- number of folders
- number of files
- number of PDFs
- last modified timestamp

If you want to inspect the full listing:

    gunzip -c data/remote_index/published/items.jsonl.gz | head

To count total PDFs in the entire country snapshot:

    gunzip -c data/remote_index/published/items.jsonl.gz | grep -i '\.pdf"' | wc -l

---

## Building a new remote snapshot (maintainers)

If ECT uploads new files and you want to refresh the public snapshot:

    bash scripts/index_remote_snapshot.sh ect_drive

Then publish the latest snapshot:

    mkdir -p data/remote_index/published
    LATEST_STATUS=$(ls -1t data/remote_index/status_*.jsonl | head -n 1)
    LATEST_ITEMS=$(ls -1t data/remote_index/items_*.jsonl  | head -n 1)

    cp "$LATEST_STATUS" data/remote_index/published/status.jsonl
    gzip -c "$LATEST_ITEMS" > data/remote_index/published/items.jsonl.gz

    python scripts/make_remote_index_summary.py

Commit and push:

    git add data/remote_index/published/
    git commit -m "Update remote snapshot"
    git push

---

## Download selected provinces

Edit `configs/provinces.txt` and add provinces (Thai names must match CSV exactly), for example:

    ลำปาง
    เชียงใหม่

Then run:

    bash scripts/sync_selected_from_csv.sh ect_drive

Files will be downloaded into:

    data/raw/<จังหวัด>/...

The original ECT folder structure is preserved.

---

## OCR pipeline (Typhoon API)

### 1) Set API credentials

Export environment variables:

    export TYPHOON_BASE_URL="https://api.opentyphoon.ai/v1"
    export TYPHOON_API_KEY="YOUR_API_KEY"

You can add these to your `~/.zshrc` if you prefer.

### 2) Run OCR

Activate environment:

    source .venv/bin/activate

Run OCR:

    python scripts/run_typhoon_ocr.py

The script:

- walks through `data/raw/`
- mirrors folder structure into `data/ocr/`
- processes PDFs page by page
- writes structured outputs (JSON / CSV depending on configuration)

You can configure:

- model version
- rate limits
- chunk size
- parallel workers

via `configs/ocr.yaml`.

---

## Collaboration model

1. Check `summary.md` to see which provinces have uploaded PDFs.
2. Agree on which province you will process.
3. Add province to your local `configs/provinces.txt`.
4. Run sync.
5. Run OCR.
6. Share back machine-readable results.

The remote snapshot ensures everyone knows:

- what ECT has uploaded
- which provinces are complete
- whether new files have appeared

---

## Versioning

Stable milestones are tagged (e.g., `v0.1`).

Check tags:

    git tag

See details:

    git show v0.1

---

## Philosophy

- Preserve raw structure exactly.
- Separate raw data, OCR output, and published metadata.
- Keep repository reproducible.
- Make collaboration modular and scalable.

This project is designed to handle ~100,000 polling stations across 77 provinces in a structured, reproducible way.
