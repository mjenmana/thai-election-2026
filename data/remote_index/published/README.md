# Remote Drive Snapshot (Published)

This folder contains the **latest** snapshot of the ECT Google Drive folder structure.

## Files
- `status.jsonl` — per-province status rollup (small, human-checkable)
- `summary.md` / `summary.csv` — easy-to-read snapshot summary
- `items.jsonl.gz` — full file/folder listing (compressed JSONL)

## How to use

Decompress and inspect:

    gunzip -c data/remote_index/published/items.jsonl.gz | head

Example: count PDFs:

    gunzip -c data/remote_index/published/items.jsonl.gz | grep -i '\.pdf"' | wc -l
