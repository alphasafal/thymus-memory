#!/bin/sh
# Start Kaggle configs one after another, keeping at most two GPU notebooks running.
# Usage: scripts/kaggle_queue.sh <cache.tar.gz> kaggle/configs/a.json kaggle/configs/b.json ...
set -u
cd "$(dirname "$0")/.."
CACHE="$1"; shift
USER_NAME="safalguptaofficial"
running() {
  n=0
  for k in $(kaggle kernels list --mine --page-size 50 2>/dev/null | awk 'NR>2 {print $1}' | grep thymus-run-); do
    kaggle kernels status "$k" 2>/dev/null | grep -qE "RUNNING|QUEUED" && n=$((n + 1))
  done
  echo "$n"
}
for config in "$@"; do
  until [ "$(running)" -lt 2 ]; do sleep 120; done
  echo "starting $config"
  for attempt in 1 2 3; do
    scripts/kaggle_push.sh "$config" "$CACHE" && break
    sleep 60
  done
  sleep 90
done
echo "all started"
