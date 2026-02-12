# thai-elections

Tools to:
- selectively sync ECT province Google Drive folders (rclone)
- snapshot/index remote folder contents (for tracking what ECT has uploaded)
- run Typhoon OCR pipeline on downloaded PDFs

## Quick start
1) Install rclone and configure a Drive remote (e.g. `ect_drive`)
2) Put province links in `configs/province_links.csv`
3) Select provinces in `configs/provinces.txt`

### Snapshot remote (what exists on ECT Drive now)
bash scripts/index_remote_snapshot.sh ect_drive

### Sync selected provinces
bash scripts/sync_selected_from_csv.sh ect_drive
