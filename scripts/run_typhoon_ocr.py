from __future__ import annotations

import os
import hashlib
import subprocess
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


def pdf_num_pages(pdf_path: Path) -> int:
    # Requires poppler: `brew install poppler`
    # pdfinfo output includes: "Pages:          3"
    try:
        out = subprocess.check_output(["pdfinfo", str(pdf_path)], text=True, stderr=subprocess.STDOUT)
        for line in out.splitlines():
            if line.strip().startswith("Pages:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:
        pass
    return 1


def main() -> None:
    base_url = os.environ.get("TYPHOON_BASE_URL")
    api_key = os.environ.get("TYPHOON_API_KEY")
    model = os.environ.get("TYPHOON_MODEL", "typhoon-ocr")

    if not base_url or not api_key:
        raise SystemExit("Missing TYPHOON_BASE_URL / TYPHOON_API_KEY")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    pdfs = sorted([p for p in RAW_ROOT.rglob("*.pdf") if p.is_file()])
    if not pdfs:
        raise SystemExit("No PDFs found under data/raw")

    # Load previous manifest if exists
    prev_map = {}
    if MANIFEST_PATH.exists():
        prev = pd.read_parquet(MANIFEST_PATH)
        for _, r in prev.iterrows():
            prev_map[(r["rel_path"], r["fingerprint"])] = r.get("status", "")

    rows = []

    for pdf in tqdm(pdfs, desc="OCR"):
        rel = str(pdf.relative_to(RAW_ROOT))
        fp = fingerprint(pdf)

        out_path = OUT_ROOT / (rel.replace("/", "__") + ".md")

        # Skip if unchanged and output exists
        if (rel, fp) in prev_map and out_path.exists():
            rows.append(dict(rel_path=rel, fingerprint=fp, status="skipped", out_md=str(out_path)))
            continue

        try:
            n_pages = pdf_num_pages(pdf)

            md_parts = []
            for page in range(1, n_pages + 1):
                md = ocr_document(
                    pdf_or_image_path=str(pdf),
                    page_num=page,            # <-- critical
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                )
                md_parts.append(f"\n\n<!-- PAGE {page}/{n_pages} -->\n\n{md}")

            out_path.write_text("\n".join(md_parts), encoding="utf-8")

            rows.append(dict(
                rel_path=rel,
                fingerprint=fp,
                status="ok",
                out_md=str(out_path),
                n_pages=n_pages,
            ))

        except Exception as e:
            rows.append(dict(
                rel_path=rel,
                fingerprint=fp,
                status="error",
                out_md=str(out_path),
                error=str(e),
            ))

    pd.DataFrame(rows).to_parquet(MANIFEST_PATH, index=False)
    print("Saved manifest to", MANIFEST_PATH)


if __name__ == "__main__":
    main()
