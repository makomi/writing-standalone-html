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
assert_exit 1 tests/fixtures/bad-rgba.html "rgba() outside tokens fails"
assert_exit 1 tests/fixtures/bad-named-colour.html "named colour outside tokens fails"
assert_exit 1 tests/fixtures/bad-token-drift.html "edited token block fails"
assert_exit 1 tests/fixtures/bad-fiction.html "surviving upstream brand fails"
assert_exit 1 tests/fixtures/bad-script-colour.html "colour in a style assignment fails"
assert_exit 1 tests/fixtures/bad-script-style-element.html "colour in a built stylesheet fails"
assert_exit 1 tests/fixtures/bad-script-insert-rule.html "colour in an inserted rule fails"
assert_exit 1 tests/fixtures/bad-script-markup-attr.html "colour in a built style attribute fails"
assert_exit 0 tests/fixtures/good-script-colour.html "colour outside a style assignment passes"
assert_output_contains "external" tests/fixtures/bad-external-ref.html "names the external-ref check"
assert_output_contains "raw hex" tests/fixtures/bad-raw-hex.html "names the raw-hex check"
assert_output_contains "rgba(" tests/fixtures/bad-rgba.html "quotes the offending colour function"
assert_output_contains "tomato" tests/fixtures/bad-named-colour.html "quotes the offending colour name"
assert_output_contains "token block" tests/fixtures/bad-token-drift.html "names the token-block check"
assert_output_contains "fiction" tests/fixtures/bad-fiction.html "names the fiction check"
assert_output_contains "script colour" tests/fixtures/bad-script-colour.html "names the script-colour check"
assert_output_contains "#d97757" tests/fixtures/bad-script-style-element.html "quotes the colour written into a stylesheet"
assert_output_contains "rgba(" tests/fixtures/bad-script-insert-rule.html "quotes the colour pushed into a sheet"
assert_output_contains "style attribute" tests/fixtures/bad-script-markup-attr.html "says the colour is in a built attribute"

exit $fail
