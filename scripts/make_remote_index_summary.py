#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

PUBLISHED = Path("data/remote_index/published")
STATUS = PUBLISHED / "status.jsonl"
ITEMS_GZ = PUBLISHED / "items.jsonl.gz"


def load_status():
    rows = []
    with STATUS.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def main():
    status_rows = load_status()

    # status.jsonl should already have per-province rollups produced by your index script.
    # We’ll output a compact CSV + MD from it.
    out_csv = PUBLISHED / "summary.csv"
    out_md = PUBLISHED / "summary.md"

    # Try common fields; adjust if your status schema differs
    # Expecting something like: province, folder_id, n_items, n_files, n_dirs, last_modtime, ok/error
    headers = [
        "province",
        "folder_id",
        "ok",
        "n_items",
        "n_files",
        "n_dirs",
        "latest_modtime",
    ]

    def get(r, k):
        return r.get(k, "")

    with out_csv.open("w", encoding="utf-8") as f:
        f.write(",".join(headers) + "\n")
        for r in status_rows:
            row = [str(get(r, h)).replace("\n", " ").replace(",", ";") for h in headers]
            f.write(",".join(row) + "\n")

    # Markdown table
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Remote index summary (latest snapshot)\n\n")
        f.write(f"- Status file: `{STATUS.as_posix()}`\n")
        f.write(f"- Full index (compressed): `{ITEMS_GZ.as_posix()}`\n\n")
        f.write("| Province | OK | Items | Files | Dirs | Latest modtime |\n")
        f.write("|---|---:|---:|---:|---:|---|\n")
        for r in status_rows:
            f.write(
                f"| {get(r,'province')} | {get(r,'ok')} | {get(r,'n_items')} | {get(r,'n_files')} | {get(r,'n_dirs')} | {get(r,'latest_modtime')} |\n"
            )

    print("Wrote:")
    print(" -", out_csv)
    print(" -", out_md)


if __name__ == "__main__":
    main()
