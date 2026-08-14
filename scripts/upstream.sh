#!/usr/bin/env bash
# Borrow an ephemeral clone of upstream, then give it back.
#
#   ./scripts/upstream.sh fetch   clone --depth 1 into .upstream/
#   ./scripts/upstream.sh clean   delete .upstream/
#
# The skill keeps no permanent copy of upstream (decision 0006).
# .upstream/ is git-ignored and must not survive an ingest run.
set -euo pipefail
cd "$(dirname "$0")/.."

REPO="https://github.com/anthropics/html-effectiveness.git"
DIR=".upstream"

case "${1:-}" in
  fetch)
    if [ -d "$DIR/.git" ]; then
      echo "upstream: reusing existing clone at $DIR"
    else
      rm -rf "$DIR"
      echo "upstream: cloning $REPO (depth 1)"
      git clone --quiet --depth 1 "$REPO" "$DIR"
    fi
    commit=$(git -C "$DIR" rev-parse HEAD)
    count=$(find "$DIR" -maxdepth 1 -name '[0-9][0-9]-*.html' | wc -l)
    echo "upstream: $DIR at $commit"
    echo "upstream: $count numbered files"
    ;;
  clean)
    if [ -d "$DIR" ]; then
      rm -rf "$DIR"
      echo "upstream: removed $DIR"
    else
      echo "upstream: nothing to remove"
    fi
    ;;
  *)
    echo "usage: ./scripts/upstream.sh {fetch|clean}" >&2
    exit 2
    ;;
esac
