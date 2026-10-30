#!/usr/bin/env python3
"""Generate self-contained skill contract copies from a single maintained source."""

from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "docs/project-contract.md").read_bytes()
for folder in (root / "skills").glob("video-*"):
    (folder / "references/integration.md").write_bytes(source)
print("Synced project contract to all video-* skills")
