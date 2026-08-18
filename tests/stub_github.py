#!/usr/bin/env python3
"""Serve canned GitHub API responses so drift tests cost no budget.

Unauthenticated GitHub allows 60 calls an hour. `test_update.sh` used
to spend about eleven of them per run, so six suite runs emptied the
budget and drift detection then skipped -- a green run hiding an
unexercised suite. Every assertion that checks classification runs
against this stub instead. One live call stays in the suite as the
integration check that the real API still answers in the shape
`lib/github.py` reads.

The stub is the real HTTP path, not a monkeypatch: `update.sh` reaches
it through GITHUB_API_BASE, so urllib, the JSON decode and the tree
filter all run exactly as they do against github.com.

Usage:

    python3 tests/stub_github.py <mode> -- <command> [args...]

Starts the server, points GITHUB_API_BASE at it, runs the command and
exits with the command's status. The server never outlives the child.

Modes:
    current    the tree matches templates/MANIFEST.json exactly
    drifted    one blob SHA differs from the manifest
    added      one numbered file the manifest does not record
    empty      a tree with no numbered files
    truncated  GitHub reports the tree as incomplete
"""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HEAD = "1234567890abcdef1234567890abcdef12345678"
MODES = ("current", "drifted", "added", "empty", "truncated")


def manifest_blobs():
    """upstream filename -> blob SHA, read from the real manifest.

    Deriving the canned tree from the manifest is what keeps the stub
    honest: a conversion that re-stamps MANIFEST.json moves this in the
    same commit, so "unchanged: 20" cannot rot into a lie.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "templates", "MANIFEST.json"),
              encoding="utf-8") as fh:
        manifest = json.load(fh)
    return {e["upstream_source"]: e["upstream_blob_sha"]
            for e in manifest["files"]}


def tree_for(mode):
    """The `tree` array and `truncated` flag GitHub would return."""
    blobs = manifest_blobs()
    if mode == "empty":
        blobs = {}
    elif mode == "drifted":
        first = sorted(blobs)[0]
        blobs[first] = "0" * 40
    elif mode == "added":
        blobs["99-brand-new-upstream-file.html"] = "f" * 40

    entries = [{"path": p, "type": "blob", "mode": "100644", "sha": s}
               for p, s in sorted(blobs.items())]
    # Entries the filter must drop: unnumbered, non-HTML, and a tree.
    entries += [
        {"path": "README.md", "type": "blob", "mode": "100644",
         "sha": "a" * 40},
        {"path": "index.html", "type": "blob", "mode": "100644",
         "sha": "b" * 40},
        {"path": "assets", "type": "tree", "mode": "040000",
         "sha": "c" * 40},
    ]
    return entries, mode == "truncated"


class Handler(BaseHTTPRequestHandler):
    mode = "current"

    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.endswith("/commits"):
            self._send(200, [{"sha": HEAD}])
            return
        if "/git/trees/" in path:
            entries, truncated = tree_for(self.mode)
            self._send(200, {"sha": HEAD, "truncated": truncated,
                             "tree": entries})
            return
        # An unrecognised route is a stub bug, not a passing test. Say
        # so in the body rather than answering something plausible.
        self._send(404, {"message": f"stub_github.py has no route {path}"})

    def log_message(self, *args):
        """Silence the per-request line; the suite prints its own."""


def main(argv):
    if len(argv) < 4 or argv[2] != "--":
        print(__doc__, file=sys.stderr)
        return 2
    mode = argv[1]
    if mode not in MODES:
        print(f"stub_github.py: unknown mode {mode!r}; "
              f"expected one of {', '.join(MODES)}", file=sys.stderr)
        return 2

    Handler.mode = mode
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    env = dict(os.environ)
    env["GITHUB_API_BASE"] = f"http://{host}:{port}/repos/stub/html-effectiveness"
    # A token would make urllib send an Authorization header to
    # localhost. Harmless, but the live budget check reads GITHUB_TOKEN
    # too, so drop it here to keep the two paths visibly separate.
    env.pop("GITHUB_TOKEN", None)
    try:
        return subprocess.call(argv[3:], env=env)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
