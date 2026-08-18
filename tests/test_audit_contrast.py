"""The rules inside scripts/audit-contrast.js must hold.

The cases are JavaScript, in tests/test_audit_contrast.js, because the
thing under test is JavaScript. This wrapper exists for the skip: node
is not a dependency of this repo and must not become one, so a machine
without it reports SKIP and exits 0, the way test_js_syntax.py does.
run-all.sh counts a skip as a skip rather than a pass.

The audit itself needs a browser and is therefore not a suite member.
What is pinned here is its pure half — colour parsing, contrast, the
rect geometry, the node filter, the large-text threshold and the ground
rule. The DOM walk stays behind that export and is unexercised.
"""

import pathlib
import shutil
import subprocess
import sys

CASES = pathlib.Path(__file__).with_suffix(".js")


def main():
    node = shutil.which("node")
    if not node:
        print("SKIP: node not found; the contrast audit's rules were not checked")
        return 0

    result = subprocess.run([node, str(CASES)], capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode and not result.stdout:
        # node fell over before the cases ran -- a syntax error in the
        # audit, or an export that stopped existing. Say so, rather than
        # leaving an empty failure.
        print(f"FAIL: node exited {result.returncode} without running the cases")
    return 1 if result.returncode else 0


if __name__ == "__main__":
    sys.exit(main())
