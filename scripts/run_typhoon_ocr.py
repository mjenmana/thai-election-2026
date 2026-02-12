from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from tqdm import tqdm
from typhoon_ocr import ocr_document

RAW_ROOT = Path("data/raw")
OUT_ROOT_DEFAULT = Path("data/processed/ocr_markdown")
MANIFEST_JSONL_DEFAULT = Path("data/manifests/ocr_manifest.jsonl")
MANIFEST_PARQUET_DEFAULT = Path("data/manifests/ocr_manifest.parquet")


def fingerprint(path: Path) -> str:
    stat = path.stat()
    h = hashlib.sha1()
    h.update(f"{stat.st_size}:{int(stat.st_mtime)}".encode("utf-8"))
    return h.hexdigest()


def pdf_num_pages(pdf_path: Path) -> int:
    # Requires poppler: `brew install poppler`
    try:
        out = subprocess.check_output(
            ["pdfinfo", str(pdf_path)], text=True, stderr=subprocess.STDOUT
        )
        for line in out.splitlines():
            if line.strip().startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return 1


def read_existing_fingerprint(out_path: Path) -> Optional[str]:
    """
    Reads the fingerprint embedded in the first lines of the output markdown.
    We write a header like:
      <!-- rel_path=... -->
      <!-- fingerprint=... -->
    """
    if not out_path.exists():
        return None
    try:
        with out_path.open("r", encoding="utf-8") as f:
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("<!-- fingerprint=") and line.endswith("-->"):
                    return line[len("<!-- fingerprint=") : -len("-->")].strip()
    except Exception:
        return None
    return None


def ocr_one_pdf(
    pdf: Path,
    rel: str,
    fp: str,
    out_path: Path,
    base_url: str,
    api_key: str,
    model: str,
    retries: int,
    retry_base_sleep: float,
) -> Dict[str, Any]:
    t0 = time.time()
    try:
        n_pages = pdf_num_pages(pdf)
        md_parts = []

        # header for robust skip even without manifest
        md_parts.append(f"<!-- rel_path={rel} -->")
        md_parts.append(f"<!-- fingerprint={fp} -->")
        md_parts.append(f"<!-- model={model} -->")
        md_parts.append("")

        for page in range(1, n_pages + 1):
            last_err: Optional[Exception] = None
            for attempt in range(retries + 1):
                try:
                    md = ocr_document(
                        pdf_or_image_path=str(pdf),
                        page_num=page,
                        base_url=base_url,
                        api_key=api_key,
                        model=model,
                    )
                    md_parts.append(f"\n\n<!-- PAGE {page}/{n_pages} -->\n\n{md}")
                    last_err = None
                    break
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    last_err = e
                    # backoff + jitter
                    sleep_s = retry_base_sleep * (2**attempt) + random.random()
                    time.sleep(sleep_s)

            if last_err is not None:
                raise last_err

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(md_parts), encoding="utf-8")

        return {
            "rel_path": rel,
            "fingerprint": fp,
            "status": "ok",
            "out_md": str(out_path),
            "n_pages": n_pages,
            "seconds": round(time.time() - t0, 3),
        }

    except Exception as e:
        return {
            "rel_path": rel,
            "fingerprint": fp,
            "status": "error",
            "out_md": str(out_path),
            "error": str(e),
            "seconds": round(time.time() - t0, 3),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-root", default=str(RAW_ROOT))
    ap.add_argument("--out-root", default=str(OUT_ROOT_DEFAULT))
    ap.add_argument("--manifest-jsonl", default=str(MANIFEST_JSONL_DEFAULT))
    ap.add_argument("--manifest-parquet", default=str(MANIFEST_PARQUET_DEFAULT))
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-seconds", type=int, default=7200)
    ap.add_argument("--max-files", type=int, default=0, help="0 = no limit")
    ap.add_argument("--model", default=os.environ.get("TYPHOON_MODEL", "typhoon-ocr"))
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--retry-sleep", type=float, default=2.0)
    args = ap.parse_args()

    raw_root = Path(args.raw_root)
    out_root = Path(args.out_root)
    manifest_jsonl = Path(args.manifest_jsonl)
    manifest_parquet = Path(args.manifest_parquet)

    base_url = os.environ.get("TYPHOON_BASE_URL")
    api_key = os.environ.get("TYPHOON_API_KEY")
    model = args.model

    if not base_url or not api_key:
        raise SystemExit("Missing TYPHOON_BASE_URL / TYPHOON_API_KEY")

    out_root.mkdir(parents=True, exist_ok=True)
    manifest_jsonl.parent.mkdir(parents=True, exist_ok=True)
    manifest_parquet.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted([p for p in raw_root.rglob("*.pdf") if p.is_file()])
    if not pdfs:
        raise SystemExit(f"No PDFs found under {raw_root}")

    # Load previous JSONL manifest into a map (so we can skip without parquet)
    done_map: Dict[Tuple[str, str], str] = {}
    if manifest_jsonl.exists():
        with manifest_jsonl.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    done_map[(r.get("rel_path", ""), r.get("fingerprint", ""))] = r.get(
                        "status", ""
                    )
                except Exception:
                    continue

    start = time.time()

    # Build tasks list with robust skip:
    # - output exists AND embedded fingerprint matches => skip
    tasks = []
    rows = []

    for pdf in pdfs:
        rel = str(pdf.relative_to(raw_root))
        fp = fingerprint(pdf)
        out_path = (out_root / rel).with_suffix(".md")

        existing_fp = read_existing_fingerprint(out_path)

        if existing_fp == fp:
            rows.append(
                {
                    "rel_path": rel,
                    "fingerprint": fp,
                    "status": "skipped",
                    "out_md": str(out_path),
                }
            )
            continue

        if (rel, fp) in done_map and out_path.exists():
            rows.append(
                {
                    "rel_path": rel,
                    "fingerprint": fp,
                    "status": "skipped",
                    "out_md": str(out_path),
                }
            )
            continue

        tasks.append((pdf, rel, fp, out_path))

    # Write initial skipped rows to JSONL immediately (so file isn't "empty while running")
    with manifest_jsonl.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if not tasks:
        print("Nothing to OCR (all PDFs already processed with matching fingerprint).")
        # also refresh parquet
        df = pd.DataFrame(rows)
        if not df.empty:
            df.to_parquet(manifest_parquet, index=False)
        return

    processed = 0
    to_process = (
        tasks[: args.max_files] if args.max_files and args.max_files > 0 else tasks
    )

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = []
        for pdf, rel, fp, out_path in to_process:
            futs.append(
                ex.submit(
                    ocr_one_pdf,
                    pdf,
                    rel,
                    fp,
                    out_path,
                    base_url,
                    api_key,
                    model,
                    args.retries,
                    args.retry_sleep,
                )
            )

        for fut in tqdm(as_completed(futs), total=len(futs), desc="OCR"):
            r = fut.result()
            processed += 1

            # append row immediately
            with manifest_jsonl.open("a", encoding="utf-8") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

            # stop after max-seconds (chunking)
            if (time.time() - start) >= args.max_seconds:
                print(
                    f"\nReached --max-seconds={args.max_seconds}. Stopping chunk early."
                )
                break

    # Rebuild parquet from jsonl (single source of truth)
    all_rows = []
    with manifest_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                all_rows.append(json.loads(line))
            except Exception:
                continue

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df.to_parquet(manifest_parquet, index=False)

    print(f"Done chunk. Wrote JSONL manifest: {manifest_jsonl}")
    print(f"Wrote parquet manifest: {manifest_parquet}")
    print(f"Processed this run: {processed} (workers={args.workers}, model={model})")


if __name__ == "__main__":
    main()
