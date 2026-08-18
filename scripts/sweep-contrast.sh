#!/usr/bin/env bash
# Run scripts/audit-contrast.js over many pages in one browser session.
#
#   ./scripts/sweep-contrast.sh                        every template, both themes
#   ./scripts/sweep-contrast.sh templates/09-*.html    named files
#   ./scripts/sweep-contrast.sh --theme dark           one theme
#   ./scripts/sweep-contrast.sh --driver 'my-adapter'  a driver of your own
#
# One launch per page costs about twelve seconds, so a repo-wide sweep
# by hand is forty launches and eight minutes. One session per theme is
# about thirteen seconds, which is the difference between a sweep run
# after every template edit and a sweep run twice a month.
#
# This is an audit aid, not a suite member: it needs a browser, and a
# browser must not become a dependency of tests/run-all.sh.
# audit-contrast.js is untouched and stays usable against a single
# loaded page by hand.
#
# The driver. The concrete browser invocation is machine-local and this
# repo carries none (decision 0008). Give one with --driver, or leave
# the default to the `sweep-driver:` line in .claude/browsing.md, which
# is git-ignored and describes this machine only. Either way the command
# is invoked as
#
#     <driver> <path-to-audit-contrast.js> <url>...
#
# and must print, on stdout, one JSON object mapping every url it was
# given to that page's findings — the audit's own array, parsed. Its own
# chatter goes to stderr. A non-zero exit fails the sweep, and so does a
# url the driver answered for with nothing.
#
# Exit: 0 every page clean, 1 findings, 2 the sweep could not run.
set -uo pipefail
cd "$(dirname "$0")/.."

driver=""
themes="light dark"
files=()

while [ $# -gt 0 ]; do
  case "$1" in
    --driver)
      [ $# -ge 2 ] || { echo "sweep: --driver needs a command" >&2; exit 2; }
      driver="$2"; shift 2 ;;
    --theme)
      [ $# -ge 2 ] || { echo "sweep: --theme needs light, dark or both" >&2; exit 2; }
      case "$2" in
        light|dark) themes="$2" ;;
        both)       themes="light dark" ;;
        *) echo "sweep: unknown theme '$2'" >&2; exit 2 ;;
      esac
      shift 2 ;;
    -h|--help)
      sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --*)
      echo "sweep: unknown option '$1'" >&2; exit 2 ;;
    *)
      files+=("$1"); shift ;;
  esac
done

if [ -z "$driver" ]; then
  if [ ! -f .claude/browsing.md ]; then
    echo "sweep: no --driver given and no .claude/browsing.md to default from" >&2
    echo "sweep: AGENTS.md, under 'Browsing and the theme check', says what a driver has to do" >&2
    exit 2
  fi
  driver=$(sed -n 's/^ *sweep-driver: *//p' .claude/browsing.md | head -1)
  if [ -z "$driver" ]; then
    echo "sweep: .claude/browsing.md carries no 'sweep-driver:' line" >&2
    exit 2
  fi
fi

if [ ${#files[@]} -eq 0 ]; then
  shopt -s nullglob
  files=(templates/*.html)
  if [ ${#files[@]} -eq 0 ]; then
    echo "sweep: no templates found in templates/" >&2
    exit 1
  fi
fi

python3 - "$driver" "$themes" "${files[@]}" <<'PY'
import json
import os
import pathlib
import subprocess
import sys
import time

driver, themes = sys.argv[1], sys.argv[2].split()
files = [pathlib.Path(p).resolve() for p in sys.argv[3:]]
audit = str(pathlib.Path("scripts/audit-contrast.js").resolve())


def cannot_run(message):
    """Exit 2. A sweep that could not run is not a sweep that found
    nothing, and the two must not share an exit code."""
    print(message, file=sys.stderr)
    raise SystemExit(2)

# No writing to /tmp in this sandbox, and a theme copy must never be
# written next to the template it copies.
tmpdir = os.environ.get("TMPDIR")
if not tmpdir:
    cannot_run("sweep: TMPDIR is unset, and there is nowhere else to put the theme copies")
work = pathlib.Path(tmpdir) / "sweep-contrast"
work.mkdir(parents=True, exist_ok=True)

# Templates ship without data-theme so they follow the reader's system
# setting, which gives a headless browser light. Dark needs a copy.
def page(src, theme):
    if theme == "light":
        return src
    out = work / (src.stem + ".dark.html")
    html = src.read_text()
    marked = html.replace("<html lang=\"en\">", "<html lang=\"en\" data-theme=\"dark\">", 1)
    if marked == html:
        cannot_run(f"sweep: {src.name} has no <html lang=\"en\"> to set the theme on")
    out.write_text(marked)
    return out


def sweep(theme):
    urls = ["file://" + str(page(f, theme)) for f in files]
    print(f"sweep: {theme}, {len(urls)} page(s), one session", flush=True)
    started = time.time()
    run = subprocess.run(["bash", "-c", driver + ' "$@"', "sweep-driver", audit] + urls,
                         capture_output=True, text=True)
    sys.stderr.write(run.stderr)
    if run.returncode != 0:
        cannot_run(f"sweep: the driver exited {run.returncode}")
    try:
        results = json.loads(run.stdout)
    except json.JSONDecodeError as e:
        cannot_run(f"sweep: the driver's stdout is not the JSON object the contract asks for ({e})")
    print(f"sweep: {theme} took {time.time() - started:.0f}s", flush=True)

    failed = 0
    for f, url in zip(files, urls):
        if url not in results:
            cannot_run(f"sweep: the driver answered for {len(results)} url(s) and not for {url}")
        findings = results[url]
        if findings:
            failed += 1
            print(f"  FAIL {theme:5} {f.name}")
            body = json.dumps(findings, indent=2, ensure_ascii=False)
            print("    " + body.replace("\n", "\n    "))
        else:
            print(f"  ok   {theme:5} {f.name}")
    return failed


total = sum(sweep(theme) for theme in themes)
pages = len(files) * len(themes)
if total:
    print(f"sweep: {total} of {pages} page(s) carry findings")
    sys.exit(1)
print(f"sweep: {pages} page(s) clean")
PY
