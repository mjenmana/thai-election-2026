#!/usr/bin/env python3
import json, os, subprocess, sys, datetime

REMOTE = sys.argv[1]  # e.g. ect_drive
PROVINCE = sys.argv[2]  # Thai name
FOLDER_ID = sys.argv[3]  # drive folder id

ts = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

cmd = [
    "rclone",
    "lsjson",
    f"{REMOTE}:",
    "--drive-root-folder-id",
    FOLDER_ID,
    "--recursive",
    "--fast-list",
    "--metadata",
    "--drive-skip-gdocs",
]

p = subprocess.run(cmd, capture_output=True, text=True)

stdout = (p.stdout or "").strip()
stderr = (p.stderr or "").strip()

# Always emit a status record, even on failure/empty
status = {
    "ts_utc": ts,
    "province": PROVINCE,
    "folder_id": FOLDER_ID,
    "ok": False,
    "rclone_returncode": p.returncode,
    "error": None,
    "n_items": 0,
    "n_dirs": 0,
    "n_files": 0,
    "n_pdfs": 0,
    "latest_modtime": None,
}

items = []

if p.returncode != 0:
    status["error"] = stderr or "rclone failed with nonzero exit"
elif not stdout:
    # this is exactly your current problem: json.load fails on empty
    status["error"] = "empty stdout from rclone (no JSON produced)"
else:
    try:
        arr = json.loads(stdout)  # should be a JSON array
        if not isinstance(arr, list):
            status["error"] = "rclone output is not a JSON array"
        else:
            items = arr
            status["ok"] = True
    except Exception as e:
        status["error"] = f"json parse error: {e}"

# compute counts if ok
if status["ok"]:
    status["n_items"] = len(items)
    for it in items:
        is_dir = bool(it.get("IsDir"))
        status["n_dirs"] += 1 if is_dir else 0
        status["n_files"] += 0 if is_dir else 1
        path = (it.get("Path") or "").lower()
        if (not is_dir) and path.endswith(".pdf"):
            status["n_pdfs"] += 1
        mt = it.get("ModTime")
        if mt and (status["latest_modtime"] is None or mt > status["latest_modtime"]):
            status["latest_modtime"] = mt

# Print: first the status line to stderr marker? no—caller will redirect
print(json.dumps(status, ensure_ascii=False))
# Then print each item as JSONL to stdout? We'll let caller handle separately.
for it in items:
    it2 = dict(it)
    it2["province"] = PROVINCE
    it2["folder_id"] = FOLDER_ID
    it2["indexed_ts_utc"] = ts
    print(json.dumps(it2, ensure_ascii=False))
