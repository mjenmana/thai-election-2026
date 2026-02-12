from __future__ import annotations

import os
import hashlib
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from typhoon_ocr import ocr_document

RAW_ROOT = Path("data/raw")
OUT_ROOT = Path("data/processed/ocr_markdown")
MANIFEST_PATH = Path("data/manifests/ocr_manifest.parquet")


def fingerprint(path: Path) -> str:
    stat = path.stat()
    h = hashlib.sha1()
    h.update(f"{stat.st_size}:{int(stat.st_mtime)}".encode())
    return h.hexdigest()


def main():

    base_url = os.environ.get("TYPHOON_BASE_URL")
    api_key = os.environ.get("TYPHOON_API_KEY")
    model = os.environ.get("TYPHOON_MODEL")

    if not base_url or not api_key or not model:
        raise SystemExit(
            "Missing TYPHOON_BASE_URL / TYPHOON_API_KEY / TYPHOON_MODEL"
        )

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted([p for p in RAW_ROOT.rglob("*.pdf") if p.is_file()])
    if not pdfs:
        raise SystemExit("No PDFs found under data/raw")

    # Load previous manifest if exists
    if MANIFEST_PATH.exists():
        prev = pd.read_parquet(MANIFEST_PATH)
        prev_map = {(r.rel_path, r.fingerprint): r.status for _, r in prev.iterrows()}
    else:
        prev_map = {}

    rows = []

    for pdf in tqdm(pdfs, desc="OCR"):
        rel = str(pdf.relative_to(RAW_ROOT))
        fp = fingerprint(pdf)
        out_path = OUT_ROOT / (rel.replace("/", "__") + ".md")

        if (rel, fp) in prev_map and out_path.exists():
            rows.append(
                dict(
                    rel_path=rel,
                    fingerprint=fp,
                    status="skipped",
                    out_md=str(out_path),
                )
            )
            continue

        try:
            md = ocr_document(
                str(pdf),
                base_url=base_url,
                api_key=api_key,
                model=model,
            )

            out_path.write_text(md, encoding="utf-8")

            rows.append(
                dict(
                    rel_path=rel,
                    fingerprint=fp,
                    status="ok",
                    out_md=str(out_path),
                )
            )

        except Exception as e:
            rows.append(
                dict(
                    rel_path=rel,
                    fingerprint=fp,
                    status="error",
                    out_md=str(out_path),
                    error=str(e),
                )
            )

    pd.DataFrame(rows).to_parquet(MANIFEST_PATH, index=False)
    print("Saved manifest to", MANIFEST_PATH)


if __name__ == "__main__":
    main()
