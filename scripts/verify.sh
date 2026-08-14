#!/usr/bin/env bash
# Mechanical verification for standalone HTML templates.
# Usage: ./scripts/verify.sh [file...]   (defaults to templates/*.html)
set -uo pipefail
cd "$(dirname "$0")/.."

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  shopt -s nullglob
  files=(templates/*.html)
  if [ ${#files[@]} -eq 0 ]; then
    echo "verify: no templates found in templates/" >&2
    exit 1
  fi
fi

echo "verify: checking ${#files[@]} file(s)"
python3 lib/checks.py "${files[@]}"
status=$?
if [ $status -eq 0 ]; then
  echo "verify: all ${#files[@]} file(s) passed"
fi
exit $status
