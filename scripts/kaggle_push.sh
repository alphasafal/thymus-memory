#!/bin/sh
# Bundle the code into a private Kaggle dataset and start a private GPU notebook run.
# Usage: scripts/kaggle_push.sh <kaggle-config.json>   (see kaggle/configs/)
set -eu
cd "$(dirname "$0")/.."
CONFIG="${1:?usage: scripts/kaggle_push.sh kaggle/configs/<name>.json}"
USER_NAME="$(kaggle config view 2>/dev/null | awk -F': ' '/username/ {print $2}' | tr -d ' ')"
USER_NAME="${USER_NAME:-safalguptaofficial}"
BUILD=".kaggle-build"
rm -rf "$BUILD" && mkdir -p "$BUILD/dataset" "$BUILD/kernel"

# Code bundle (no results, caches or virtualenv).
tar --exclude=.venv --exclude=results --exclude=.cache --exclude=.kaggle-build --exclude=.git \
    -czf "$BUILD/dataset/code.tar.gz" -C .. "$(basename "$PWD")"
cp "$CONFIG" "$BUILD/dataset/run_config.json"
cat > "$BUILD/dataset/dataset-metadata.json" <<META
{"title": "thymus-memory-code", "id": "$USER_NAME/thymus-memory-code", "licenses": [{"name": "other"}]}
META
if kaggle datasets status "$USER_NAME/thymus-memory-code" >/dev/null 2>&1; then
  kaggle datasets version -p "$BUILD/dataset" -m "code $(git rev-parse --short HEAD)" -r skip
else
  kaggle datasets create -p "$BUILD/dataset" -r skip   # private by default
fi

cp kaggle/run_on_kaggle.py "$BUILD/kernel/"
cat > "$BUILD/kernel/kernel-metadata.json" <<META
{
  "id": "$USER_NAME/thymus-memory-run",
  "title": "thymus-memory-run",
  "code_file": "run_on_kaggle.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": ["$USER_NAME/thymus-memory-code"],
  "competition_sources": [],
  "kernel_sources": []
}
META
# Give Kaggle a moment to process the new dataset version before the notebook starts.
sleep 60
kaggle kernels push -p "$BUILD/kernel"
echo "Started. Check with: kaggle kernels status $USER_NAME/thymus-memory-run"
