#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
mkdir -p .cache revision
if [[ -x tools/tectonic ]]; then
  compiler=./tools/tectonic
elif command -v tectonic >/dev/null 2>&1; then
  compiler=tectonic
else
  echo 'Install Tectonic (XeLaTeX-compatible) or place it at paper/tools/tectonic.' >&2
  exit 1
fi
export XDG_CACHE_HOME="$PWD/.cache"
doc="${1:-ja}"
case "$doc" in
  ja) tex=main.tex;  log=revision/build.log ;;
  en) tex=main_en.tex; log=revision/build_en.log ;;
  *)  echo "usage: build.sh [ja|en]" >&2; exit 2 ;;
esac
"$compiler" --keep-logs --keep-intermediates "$tex" > "$log" 2>&1
echo "Built $PWD/${tex%.tex}.pdf"
