#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-ect_drive}"
CSV="configs/province_links.csv"

OUTDIR="data/remote_index"
mkdir -p "$OUTDIR" "$OUTDIR/errors"

TS="$(date +%Y%m%d_%H%M%S)"

ITEMS="$OUTDIR/items_${TS}.jsonl"
STATUS="$OUTDIR/status_${TS}.jsonl"

: > "$ITEMS"
: > "$STATUS"

extract_folder_id() {
  # supports .../folders/<ID>...
  echo "$1" | sed -n 's#.*drive/folders/\([^?/\"]*\).*#\1#p'
}

tail -n +2 "$CSV" | while IFS=, read -r province url; do
  province="$(echo "${province:-}" | sed 's/^"//; s/"$//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
  url="$(echo "${url:-}" | sed 's/^"//; s/"$//; s/^[[:space:]]*//; s/[[:space:]]*$//')"
  [[ -z "$province" || -z "$url" ]] && continue

  folder_id="$(extract_folder_id "$url")"
  [[ -z "$folder_id" ]] && { echo "WARN: no folder_id for $province" >&2; continue; }

  echo "Indexing: $province"

  tmp="$OUTDIR/errors/${TS}__${province}.out"
  err="$OUTDIR/errors/${TS}__${province}.err"

  # Run python wrapper; it prints:
  #  - first line: status JSON
  #  - remaining lines: item JSONL
  python3 scripts/index_one_province.py "$REMOTE" "$province" "$folder_id" \
    > "$tmp" 2> "$err" || true

  # Append status line (line 1) even if empty file (guard)
  if [[ -s "$tmp" ]]; then
    head -n 1 "$tmp" >> "$STATUS"
    tail -n +2 "$tmp" >> "$ITEMS"
  else
    # Absolute worst case: nothing written; still emit a status record
    python3 - <<PY >> "$STATUS"
import json, datetime
print(json.dumps({
  "ts_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat()+"Z",
  "province": "${province}",
  "folder_id": "${folder_id}",
  "ok": False,
  "error": "indexer produced no output",
}, ensure_ascii=False))
PY
  fi

done

echo "Done."
echo "Items:  $ITEMS"
echo "Status: $STATUS"
echo "Errors: $OUTDIR/errors/"
