#!/usr/bin/env bash
set -euo pipefail

RAW_ROOT="${RAW_ROOT:-data/raw}"
OUT_ROOT="${OUT_ROOT:-data/processed/ocr_markdown}"
MODEL_DEFAULT="${MODEL_DEFAULT:-typhoon-ocr}"
WORKERS_DEFAULT="${WORKERS_DEFAULT:-3}"
SECONDS_DEFAULT="${SECONDS_DEFAULT:-7200}"

# Prompt helpers
prompt() {
  local msg="$1"
  local def="${2:-}"
  local ans
  if [[ -n "$def" ]]; then
    read -r -p "$msg [$def]: " ans || true
    echo "${ans:-$def}"
  else
    read -r -p "$msg: " ans || true
    echo "$ans"
  fi
}

echo "=== Typhoon OCR runner ==="
echo "RAW_ROOT:  $RAW_ROOT"
echo "OUT_ROOT:  $OUT_ROOT"
echo

# Basic env sanity
if [[ -z "${TYPHOON_BASE_URL:-}" || -z "${TYPHOON_API_KEY:-}" ]]; then
  echo "Missing env vars."
  echo "Set them like:"
  echo '  export TYPHOON_BASE_URL="https://api.opentyphoon.ai/v1"'
  echo '  export TYPHOON_API_KEY="YOUR_KEY"'
  exit 1
fi

model="$(prompt "Model" "$MODEL_DEFAULT")"
workers="$(prompt "Parallel workers" "$WORKERS_DEFAULT")"
max_seconds="$(prompt "How many seconds to run this chunk" "$SECONDS_DEFAULT")"
max_files="$(prompt "Max PDFs this run (0 = no limit)" "0")"

echo
echo "Running:"
echo "  model=$model workers=$workers max_seconds=$max_seconds max_files=$max_files"
echo

python scripts/run_typhoon_ocr.py \
  --raw-root "$RAW_ROOT" \
  --out-root "$OUT_ROOT" \
  --model "$model" \
  --workers "$workers" \
  --max-seconds "$max_seconds" \
  --max-files "$max_files"
