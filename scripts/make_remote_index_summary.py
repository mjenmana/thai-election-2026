#!/usr/bin/env python3
import json
import csv
from pathlib import Path

PUBLISHED_DIR = Path("data/remote_index/published")
STATUS_PATH = PUBLISHED_DIR / "status.jsonl"
LINKS_CSV = Path("configs/province_links.csv")

OUT_MD = PUBLISHED_DIR / "summary.md"
OUT_CSV = PUBLISHED_DIR / "summary.csv"

def clean(s):
    if s is None:
        return ""
    return str(s).replace("\ufeff", "").replace("\r", "").strip()

def to_int(x, default=0):
    try:
        if x is None or x == "":
            return default
        return int(x)
    except Exception:
        return default

def load_links(path: Path) -> list[dict]:
    """
    Read configs/province_links.csv with columns: province,folder_url
    Return list of dicts with ALL provinces present in the CSV.
    """
    out = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [clean(h).lower() for h in (reader.fieldnames or [])]

        if "province" not in (reader.fieldnames or []) or "folder_url" not in (reader.fieldnames or []):
            raise SystemExit("configs/province_links.csv must have columns: province,folder_url")

        for row in reader:
            row_norm = {clean(k).lower(): clean(v) for k, v in row.items()}
            prov = clean(row_norm.get("province", ""))
            url = clean(row_norm.get("folder_url", ""))
            if prov:
                out.append({"province": prov, "folder_url": url})
    return out

def load_status_jsonl(path: Path) -> dict:
    """
    Return mapping province -> status record
    """
    m = {}
    if not path.exists():
        return m
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            prov = clean(r.get("province", ""))
            if prov:
                r["province"] = prov
                m[prov] = r
    return m

def main():
    if not LINKS_CSV.exists():
        raise SystemExit(f"Missing: {LINKS_CSV}")

    all_provs = load_links(LINKS_CSV)           # complete roster (77 rows)
    status_map = load_status_jsonl(STATUS_PATH) # may be missing some provinces

    # Build unified rows: province roster drives everything
    rows = []
    for p in all_provs:
        prov = p["province"]
        url = p["folder_url"]
        s = status_map.get(prov, {})  # empty if never indexed

        n_files = to_int(s.get("n_files", 0), 0)
        n_pdfs  = to_int(s.get("n_pdfs", 0), 0)
        n_dirs  = to_int(s.get("n_dirs", 0), 0)
        n_items = to_int(s.get("n_items", 0), 0)

        ok_flag = bool(s.get("ok", False))

        # Your rule: "provinces without any files should be shown as not indexed"
        indexed_ok = bool(ok_flag and n_files >= 1)

        rows.append({
            "province": prov,
            "folder_url": url,
            "has_link": bool(url),
            "indexed_ok": indexed_ok,
            "raw_ok": ok_flag,  # keep for debugging
            "n_items": n_items,
            "n_dirs": n_dirs,
            "n_files": n_files,
            "n_pdfs": n_pdfs,
            "latest_modtime": clean(s.get("latest_modtime", "")),
            "ts_utc": clean(s.get("ts_utc", "")),
            "error": clean(s.get("error", "")),
            "folder_id": clean(s.get("folder_id", "")),
        })

    rows.sort(key=lambda r: r["province"])

    # ---- CSV
    csv_fields = [
        "province","folder_url","has_link",
        "indexed_ok","raw_ok",
        "n_items","n_dirs","n_files","n_pdfs",
        "latest_modtime","ts_utc","error","folder_id"
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in csv_fields})

    # ---- Markdown
    md = []
    md.append("# ECT Remote Drive Snapshot\n")
    md.append("| Province | Items | Dirs | Files | PDFs | Latest modtime (UTC) | Indexed | Link |")
    md.append("|---|---:|---:|---:|---:|---|:--:|:--:|")

    for r in rows:
        prov = r["province"]
        url = r["folder_url"]

        prov_disp = prov if not url else f"{prov} [link]({url})"
        indexed_disp = "✅" if r["indexed_ok"] else "❌"
        link_disp = "✅" if r["has_link"] else "❌"

        md.append(
            f"| {prov_disp} | {r['n_items']} | {r['n_dirs']} | {r['n_files']} | {r['n_pdfs']} | "
            f"{r['latest_modtime']} | {indexed_disp} | {link_disp} |"
        )

    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote: {OUT_MD}")
    print(f"Wrote: {OUT_CSV}")

if __name__ == "__main__":
    main()
