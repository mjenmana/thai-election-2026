# Thai Election 2026 — ECT Drive Mirror + OCR Pipeline (Typhoon OCR)

This repository allows contributors to:

1. Mirror (download) selected ECT province Google Drive folders while preserving the original folder structure.
2. Track what exists on ECT drives via a public remote index snapshot.
3. OCR downloaded PDFs into machine-readable text using Typhoon OCR (remote API).

IMPORTANT:

- The `data/` directory is ignored by git (it can be very large).
- Only code, configs, and published summaries are version-controlled.

---

## A. REQUIREMENTS (MacOS)

A1) System tools

Install Homebrew if needed, then:

brew install rclone jq git

A2) Python environment (recommended)

python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt

---

## B. CONFIGURATION

B1) rclone Google Drive remote

Create an rclone remote called "ect_drive":

rclone config

Test it:

rclone lsd ect_drive:

B2) Typhoon OCR API

Export your credentials (do NOT commit these):

export TYPHOON_BASE_URL="https://api.opentyphoon.ai/v1"
export TYPHOON_API_KEY="YOUR_API_KEY"

Test model availability:

curl -s -H "Authorization: Bearer $TYPHOON_API_KEY" \
 $TYPHOON_BASE_URL/models | jq

---

## C. REMOTE INDEX SNAPSHOT (ECT SIDE)

This indexes ALL provinces based on configs/province_links.csv
and produces:

data/remote_index/latest_snapshot.jsonl
data/remote_index/published/summary.md
data/remote_index/published/summary.csv

Run:

bash scripts/index_remote_snapshot.sh ect_drive
python scripts/make_remote_index_summary.py

The summary.md file is committed and visible on GitHub.

Columns:

- Province
- Items / Dirs / Files / PDFs
- Latest modtime (UTC)
- Indexed (remote drive successfully scanned)
- Link (whether ECT link exists in CSV)

---

## D. PUBLISH LATEST SNAPSHOT

After indexing, publish the newest snapshot:

bash scripts/publish_remote_index.sh

Then regenerate summary:

python scripts/make_remote_index_summary.py

Commit:

git add data/remote_index/published/summary.md \
 data/remote_index/published/summary.csv
git commit -m "Update remote index snapshot"
git push

---

## E. DOWNLOAD SELECTED PROVINCES

1. Edit:

configs/provinces.txt

List only provinces you want to download.

2. Sync:

bash scripts/sync_selected_from_csv.sh ect_drive

Raw files go to:

data/raw/<province>/...

Original structure is preserved exactly.

---

## F. RUN OCR (TYHOON REMOTE)

Interactive wrapper:

bash scripts/run_ocr_interactive.sh

It will ask:

- How many hours to run?
- How many parallel workers?

OCR outputs mirror raw structure:

data/ocr/<province>/...

The manifest is stored in:

data/manifests/ocr_manifest.jsonl

The manifest prevents re-processing of already OCR’d files.

---

## G. CONTRIBUTOR WORKFLOW

1. Pull latest repo
2. Run remote snapshot
3. Check summary.md to see which provinces:
   - Have ECT links
   - Have content uploaded
4. Choose a province in configs/provinces.txt
5. Sync it
6. Run OCR
7. Share processed outputs or derived datasets

---

## H. IMPORTANT DESIGN PRINCIPLES

- Remote index tracks ECT state (independent of local OCR progress).
- Raw structure is never modified.
- OCR output mirrors raw exactly.
- data/ is ignored to avoid massive git history.
- Published snapshot (summary.md) is the public monitoring layer.

---

## I. VERSIONING

Tag releases:

git tag -a v0.X -m "description"
git push origin v0.X

---

Maintainer: Mark Jenmana
Repository: thai-election-2026
Purpose: Transparent, distributed monitoring and digitisation of 2026 Thai election polling station results.
