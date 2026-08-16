"""Read, compare and stamp templates/MANIFEST.json."""

import json


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def stamp(path, manifest):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def compare(manifest, upstream_shas):
    """Classify every file into exactly one of four buckets.

    upstream_shas maps upstream filename -> current blob SHA.
    Enumerating upstream (not the manifest) is what makes a newly
    added upstream file visible.
    """
    recorded = {e["upstream_source"]: e["upstream_blob_sha"]
                for e in manifest["files"]}
    unchanged, changed, new = [], [], []
    for name, sha in upstream_shas.items():
        if name not in recorded:
            new.append(name)
        elif recorded[name] == sha:
            unchanged.append(name)
        else:
            changed.append(name)
    removed = [n for n in recorded if n not in upstream_shas]
    return {
        "unchanged": sorted(unchanged),
        "changed": sorted(changed),
        "new": sorted(new),
        "removed": sorted(removed),
    }
