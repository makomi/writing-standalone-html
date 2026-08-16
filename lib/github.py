"""Read upstream blob SHAs from the GitHub API.

GitHub returns real git blob SHAs, so the values compare directly
against a manifest recorded from a clone. Verified:
11-status-report.html reads 764665143d3731ccb5e8978898bf7d7a5e46cc5f
from both this API and `git rev-parse`.
"""

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("GITHUB_API_BASE",
                      "https://api.github.com/repos/anthropics/html-effectiveness")


class UpstreamUnavailable(Exception):
    """The check could not run. Distinct from 'upstream drifted'."""


def _get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "writing-standalone-html-update",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 403 and "rate limit" in exc.read().decode(errors="replace").lower():
            raise UpstreamUnavailable(
                "GitHub rate limit reached; set GITHUB_TOKEN or wait"
            ) from exc
        raise UpstreamUnavailable(f"HTTP {exc.code} from {url}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise UpstreamUnavailable(f"cannot reach {url}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise UpstreamUnavailable(f"malformed JSON from {url}") from exc


def head_commit():
    """Full 40-character SHA of the current upstream HEAD."""
    data = _get(f"{BASE}/commits?per_page=1")
    if not data:
        raise UpstreamUnavailable("no commits returned")
    return data[0]["sha"]


def tree_blobs(commit):
    """Map upstream filename -> blob SHA for every NN-*.html at commit."""
    data = _get(f"{BASE}/git/trees/{commit}")
    if data.get("truncated"):
        raise UpstreamUnavailable(
            "tree response truncated; upstream has outgrown a single page"
        )
    return {
        e["path"]: e["sha"]
        for e in data["tree"]
        if e["type"] == "blob"
        and e["path"].endswith(".html")
        and e["path"][:2].isdigit()
    }
