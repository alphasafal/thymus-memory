#!/bin/sh
# Bundle the code into a private Kaggle dataset and start a private GPU notebook run.
# Each config gets its own dataset and notebook (named after the config file), so several
# configs can run side by side.
# Usage: scripts/kaggle_push.sh <kaggle-config.json>   (see kaggle/configs/)
#   Download results: kaggle kernels output <user>/thymus-run-<config> -p results/kaggle/<config>
set -eu
cd "$(dirname "$0")/.."
CONFIG="${1:?usage: scripts/kaggle_push.sh kaggle/configs/<name>.json [previous-cache.tar.gz]}"
PREVIOUS_CACHE="${2:-}"   # cache.tar.gz from an earlier Kaggle run, so finished calls are reused
USER_NAME="$(kaggle config view 2>/dev/null | awk -F': ' '/username/ {print $2}' | tr -d ' ')"
USER_NAME="${USER_NAME:-safalguptaofficial}"
# Kaggle slugs allow only lowercase letters, digits and hyphens.
SLUG="$(basename "$CONFIG" .json | tr 'A-Z' 'a-z' | tr -c 'a-z0-9\n' '-')"
DATASET="thymus-code-$SLUG"
KERNEL="thymus-run-$SLUG"
BUILD=".kaggle-build/$SLUG"
rm -rf "$BUILD" && mkdir -p "$BUILD/dataset" "$BUILD/kernel"

# Code bundle (no results, caches, virtualenv or macOS metadata files; Kaggle unpacks it).
COPYFILE_DISABLE=1 tar --exclude=.venv --exclude=results --exclude=.cache --exclude=.kaggle-build \
    --exclude=.git --exclude=.pytest_cache --exclude=__pycache__ --exclude=.DS_Store --exclude='._*' \
    -czf "$BUILD/dataset/code.tar.gz" -C .. "$(basename "$PWD")"
cp "$CONFIG" "$BUILD/dataset/run_config.json"
if [ -n "$PREVIOUS_CACHE" ]; then
  # Kaggle unpacks .tar.gz uploads, so ship the cache under a name it leaves alone.
  cp "$PREVIOUS_CACHE" "$BUILD/dataset/cache.tgz.bin"
fi
cat > "$BUILD/dataset/dataset-metadata.json" <<META
{"title": "$DATASET", "id": "$USER_NAME/$DATASET", "licenses": [{"name": "other"}]}
META
if kaggle datasets status "$USER_NAME/$DATASET" >/dev/null 2>&1; then
  kaggle datasets version -p "$BUILD/dataset" -m "code $(git rev-parse --short HEAD)" -r skip
else
  kaggle datasets create -p "$BUILD/dataset" -r skip   # private by default
fi

cp kaggle/run_on_kaggle.py "$BUILD/kernel/"
cat > "$BUILD/kernel/kernel-metadata.json" <<META
{
  "id": "$USER_NAME/$KERNEL",
  "title": "$KERNEL",
  "code_file": "run_on_kaggle.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": ["$USER_NAME/$DATASET"],
  "competition_sources": [],
  "kernel_sources": []
}
META
# Wait until Kaggle has processed the new dataset version before the notebook starts.
until kaggle datasets status "$USER_NAME/$DATASET" 2>/dev/null | grep -q ready; do sleep 10; done
sleep 30
kaggle kernels push -p "$BUILD/kernel"
echo "Started. Check with: kaggle kernels status $USER_NAME/$KERNEL"
