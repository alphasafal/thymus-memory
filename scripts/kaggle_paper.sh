#!/bin/sh
# Compile paper/ on a private Kaggle CPU notebook (no local TeX needed).
# Usage: scripts/kaggle_paper.sh ; then: kaggle kernels output <user>/thymus-paper -p paper/build
set -eu
cd "$(dirname "$0")/.."
USER_NAME="$(kaggle config view 2>/dev/null | awk -F': ' '/username/ {print $2}' | tr -d ' ')"
USER_NAME="${USER_NAME:-safalguptaofficial}"
BUILD=".kaggle-build/paper" && rm -rf "$BUILD" && mkdir -p "$BUILD/dataset" "$BUILD/kernel"
COPYFILE_DISABLE=1 tar --exclude=build --exclude='._*' --exclude=.DS_Store -czf "$BUILD/dataset/paper.tgz.bin" paper
cat > "$BUILD/dataset/dataset-metadata.json" <<META
{"title": "thymus-paper-src", "id": "$USER_NAME/thymus-paper-src", "licenses": [{"name": "other"}]}
META
if kaggle datasets status "$USER_NAME/thymus-paper-src" >/dev/null 2>&1; then
  kaggle datasets version -p "$BUILD/dataset" -m "paper $(git rev-parse --short HEAD)" -r skip
else
  kaggle datasets create -p "$BUILD/dataset" -r skip
fi
cp kaggle/paper/compile.py "$BUILD/kernel/"
cat > "$BUILD/kernel/kernel-metadata.json" <<META
{"id": "$USER_NAME/thymus-paper", "title": "thymus-paper", "code_file": "compile.py", "language": "python",
 "kernel_type": "script", "is_private": true, "enable_gpu": false, "enable_internet": true,
 "dataset_sources": ["$USER_NAME/thymus-paper-src"], "competition_sources": [], "kernel_sources": []}
META
until kaggle datasets status "$USER_NAME/thymus-paper-src" 2>/dev/null | grep -q ready; do sleep 10; done
sleep 20
kaggle kernels push -p "$BUILD/kernel"
