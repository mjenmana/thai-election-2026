# Thai Election 2026 — ECT Google Drive Mirror + OCR Pipeline

This repository provides a reproducible workflow to:

1. Mirror ECT province Google Drive folders locally (PDF scans), preserving folder structure
2. Snapshot remote folder contents (track new uploads on ECT drives)
3. Run Typhoon OCR on PDFs → machine-readable text/markdown, preserving folder structure
4. Publish a public “remote snapshot summary” (so contributors can see what exists remotely)

> `data/` is ignored by git (large). Only code/configs + published summaries are tracked.

---

## A) Requirements (MacOS)

### A1) System tools

```bash
brew install rclone jq git
```

### A2) Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

---

## B) Configuration

### B1) rclone: set up a Drive remote

Create an rclone remote named `ect_drive`:

```bash
rclone config
```

Test:

```bash
rclone lsd ect_drive:
```

### B2) Typhoon OCR API

Set environment variables (do NOT commit keys):

```bash
export TYPHOON_BASE_URL="https://api.opentyphoon.ai/v1"
export TYPHOON_API_KEY="YOUR_KEY"
```

Optional: check models:

```bash
curl -s -H "Authorization: Bearer $TYPHOON_API_KEY" \
  "$TYPHOON_BASE_URL/models" | jq
```

---

## C) Key config files

### `configs/province_links.csv`

Two columns:

- `province`
- `folder_url`

Example:

```csv
province,folder_url
ลำปาง,https://drive.google.com/drive/folders/153yUnWv_2EWXSAbtsTTBE-wQYn9-6yXA
เชียงใหม่,https://drive.google.com/drive/folders/1RWvYL-2KyyyCKGjF6qj39qKkpUjI6oML?usp=sharing
ชลบุรี,
สมุทรปราการ,
```

Blank `folder_url` means ECT has not shared a link yet — we still track the province.

### `configs/provinces.txt`

Which provinces you want to download / OCR (one per line):

```txt
ลำปาง
เชียงใหม่
```

---

## D) Track ECT uploads (Remote Snapshot)

This indexes what currently exists on ECT drives (independent of what you downloaded/OCR’d).

### D1) Create a new snapshot

```bash
bash scripts/index_remote_snapshot.sh ect_drive
```

This writes a timestamped snapshot to `data/remote_index/` and updates a “latest” pointer.

### D2) Publish the snapshot outputs (public summary)

```bash
bash scripts/publish_remote_index.sh
python scripts/make_remote_index_summary.py
```

Outputs:

- `data/remote_index/published/summary.md`
- `data/remote_index/published/summary.csv`

The summary includes:

- all 77 provinces (including those without links),
- clickable `[link]`,
- `Indexed` status (whether remote scan succeeded),
- counts (items/dirs/files/pdfs),
- latest remote modtime.

### D3) Commit updated summaries

```bash
git add data/remote_index/published/summary.md \
        data/remote_index/published/summary.csv
git commit -m "Update remote snapshot summary"
git push
```

---

## E) Download selected provinces (Mirror locally)

```bash
bash scripts/sync_selected_from_csv.sh ect_drive
```

Raw files go to:

- `data/raw/<province>/...`

Folder structure is preserved exactly as on Drive.

---

## F) OCR (Typhoon OCR, remote API)

Run OCR over downloaded PDFs:

```bash
python scripts/run_typhoon_ocr.py
```

Outputs mirror raw:

- `data/ocr/<province>/...`

Manifests/logs:

- `data/manifests/ocr_manifest.jsonl` (used to track what was processed)

---

## G) Typical workflow (for contributors)

1. Pull repo + set up env
2. Run remote snapshot + check the published summary
3. Add your province(s) to `configs/provinces.txt`
4. Sync raw data
5. Run OCR
6. Share results / derived dataset back to maintainer (per province)

---

## H) Notes

- Provinces with no ECT link yet appear in the summary with `Link = ❌`.
- Provinces with links but no uploaded content yet should show `Indexed = ✅` but zero counts.
- OCR output is kept separate from raw to avoid accidental overwrites.
