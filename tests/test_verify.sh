#!/usr/bin/env bash
# Test harness for scripts/verify.sh. No framework: a failing assertion exits 1.
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

assert_exit() {
  local want="$1" file="$2" label="$3"
  ./scripts/verify.sh "$file" >/dev/null 2>&1
  local got=$?
  if [ "$got" != "$want" ]; then
    echo "ASSERT FAIL: $label — wanted exit $want, got $got"
    fail=1
  else
    echo "ok: $label"
  fi
}

assert_output_contains() {
  local needle="$1" file="$2" label="$3"
  # Capture rather than pipe: pipefail would surface verify.sh's own
  # non-zero exit and mask a successful grep.
  local out
  out=$(./scripts/verify.sh "$file" 2>&1)
  if printf '%s' "$out" | grep -q "$needle"; then
    echo "ok: $label"
  else
    echo "ASSERT FAIL: $label — output missing '$needle'"
    fail=1
  fi
}

assert_exit 0 tests/fixtures/good.html "clean file passes"
assert_exit 1 tests/fixtures/bad-external-ref.html "external ref fails"
assert_exit 1 tests/fixtures/bad-raw-hex.html "raw hex outside tokens fails"
assert_output_contains "external" tests/fixtures/bad-external-ref.html "names the external-ref check"
assert_output_contains "raw hex" tests/fixtures/bad-raw-hex.html "names the raw-hex check"

exit $fail
