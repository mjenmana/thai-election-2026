#!/usr/bin/env bash
set -euo pipefail

REMOTE="${1:-ect_drive}"

PUBLISHED_DIR="data/remote_index/published"
REMOTE_INDEX_DIR="data/remote_index"

mkdir -p "$PUBLISHED_DIR"

echo "==> [1/4] Building new snapshot for remote: $REMOTE"
bash scripts/index_remote_snapshot.sh "$REMOTE"

echo "==> [2/4] Finding latest snapshot files"
LATEST_STATUS="$(ls -1t "$REMOTE_INDEX_DIR"/status_*.jsonl | head -n 1)"
LATEST_ITEMS="$(ls -1t "$REMOTE_INDEX_DIR"/items_*.jsonl  | head -n 1)"

echo "    status: $LATEST_STATUS"
echo "    items : $LATEST_ITEMS"

echo "==> [3/4] Promoting to $PUBLISHED_DIR"
cp "$LATEST_STATUS" "$PUBLISHED_DIR/status.jsonl"
gzip -c "$LATEST_ITEMS" > "$PUBLISHED_DIR/items.jsonl.gz"

echo "==> [4/4] Generating readable summary"
python scripts/make_remote_index_summary.py

echo "✅ Done."
echo "Published files:"
ls -lah "$PUBLISHED_DIR" | sed -n '1,200p'
