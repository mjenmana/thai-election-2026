# 2026 Thai Election

Tools to:

- selectively sync ECT province Google Drive folders (rclone)
- snapshot/index remote folder contents (to track what ECT has uploaded)
- run Typhoon OCR pipeline on downloaded PDFs

This repository is designed to scale to ~100,000 polling station PDFs while remaining restart-safe and collaboration-friendly.

---

## Repository Structure

```
configs/
scripts/
data/
  raw/                         # downloaded PDFs (NOT committed)
    <province>/...
  processed/
    ocr_markdown/              # OCR outputs (NOT committed)
      <province>/...
  manifests/
    ocr_manifest.jsonl         # OCR progress tracking (NOT committed)
requirements.txt
README.md
```

### Design Principles

- `data/raw/` is immutable
- `data/processed/` mirrors raw structure exactly
- Province folder is always preserved at root
- OCR can be stopped and resumed safely
- Already-processed PDFs are skipped automatically
- Raw PDFs and OCR outputs are never committed to Git

---

## Setup (macOS)

### 1. Clone the repository

```bash
git clone https://github.com/mjenmana/thai-election-2026.git
cd thai-election-2026
```

### 2. Create and activate virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Typhoon API Setup

You must obtain your own Typhoon API key.

Set environment variables:

```bash
export TYPHOON_BASE_URL="https://api.opentyphoon.ai/v1"
export TYPHOON_API_KEY="YOUR_API_KEY"
```

To make them persistent:

```bash
echo 'export TYPHOON_BASE_URL="https://api.opentyphoon.ai/v1"' >> ~/.zshrc
echo 'export TYPHOON_API_KEY="YOUR_API_KEY"' >> ~/.zshrc
source ~/.zshrc
```

---

## Syncing Raw Data

Raw PDFs must be downloaded into:

```
data/raw/<province>/...
```

The province folder must always be the root directory.

Raw files are never committed to Git.

---

## Snapshot Remote (What Exists on ECT Drive Now)

```bash
bash scripts/index_remote_snapshot.sh ect_drive
```

This generates a JSONL snapshot of the remote structure so we can track new uploads over time.

---

## Sync Selected Provinces

```bash
bash scripts/sync_selected_from_csv.sh ect_drive
```

Province links must be listed in:

```
configs/province_links.csv
```

Selected provinces must be listed in:

```
configs/provinces.txt
```

---

## Running OCR (Interactive Mode)

Run:

```bash
./scripts/ocr.sh
```

You will be prompted for:

- Model name
- Number of parallel workers
- Maximum runtime in seconds (chunk duration)
- Optional maximum number of PDFs

The script:

- Runs in chunks (safe to interrupt)
- Resumes automatically
- Skips already processed PDFs (fingerprint-based)
- Preserves folder structure
- Writes progress to `data/manifests/ocr_manifest.jsonl`

---

## Resuming OCR

To resume processing:

```bash
./scripts/ocr.sh
```

Only new or modified PDFs will be processed.

Fingerprinting uses file size + modification time.

---

## Recommended Settings

For stable execution:

- Workers: 2–3
- Chunk duration: 3600–7200 seconds
- Model: `typhoon-ocr`

If API errors occur, reduce workers to 1–2.

---

## Manifest Tracking

Progress is written to:

```
data/manifests/ocr_manifest.jsonl
```

Each entry records:

- relative file path
- fingerprint
- status (`ok`, `skipped`, `error`)
- processing time

This enables:

- Safe restarts
- Distributed work
- Verification of completion

---

## Collaboration Workflow

Each collaborator may:

1. Sync one or more provinces into `data/raw/<province>/`
2. Run OCR locally
3. Share processed outputs separately (not via Git)

Because province is preserved in the output path, there is no overlap across contributors.

---

## Files Ignored by Git

The following are excluded:

```
data/
.venv/
__pycache__/
*.pyc
.DS_Store
```

This keeps the repository lightweight and reproducible.

---

## Versioning

Stable pipeline versions may be tagged:

```bash
git tag v0.1-ocr-pipeline
git push origin v0.1-ocr-pipeline
```

---

This repository provides a scalable, restart-safe, province-isolated OCR workflow for the 2026 Thai Election polling station results.
