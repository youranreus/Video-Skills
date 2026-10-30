#!/usr/bin/env python3
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
errors = []
for folder in sorted((root / "skills").glob("video-*")):
    if (folder / "references/integration.md").read_bytes() != (
        root / "docs/project-contract.md"
    ).read_bytes():
        errors.append(f"{folder.name}: contract copy out of date")
    text = (folder / "SKILL.md").read_text()
    if (
        not text.startswith("---\n")
        or f"name: {folder.name}\n" not in text
        or "description: " not in text
    ):
        errors.append(f"{folder.name}: invalid frontmatter")
    for ref in re.findall(r"\]\(([^)]+)\)", text):
        if (
            not ref.startswith(("http:", "https:", "#"))
            and not (folder / ref).is_file()
        ):
            errors.append(f"{folder.name}: missing {ref}")
    if not (folder / "agents/openai.yaml").is_file():
        errors.append(f"{folder.name}: missing UI metadata")
print(
    "\n".join(errors)
    if errors
    else "12 skills: frontmatter, entrypoint links and UI metadata valid"
)
sys.exit(bool(errors))
