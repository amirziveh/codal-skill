#!/usr/bin/env python3
"""generate-configs.py — Auto-generate agent config files for Codal."""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent

REFS = [
    "references/api-endpoints.md",
    "references/letter-types.md",
]
TEMPLATES = ["templates/python-client.py"]
ENDPOINTS = [
    "v1/companies — All 5,387 companies",
    "v1/categories — Letter type taxonomy",
    "v1/IndustryGroup — Industry groups",
    "v1/auditors — Auditor firms",
    "v1/financialYears?Symbol=... — Fiscal years",
    "v2/q?Symbol=...&LetterType=... — Search filings",
]

def generate():
    refs = "\n".join(f"- `{f}`" for f in REFS + TEMPLATES)
    eps = "\n".join(f"- `{e}`" for e in ENDPOINTS)
    content = f"""# Codal API — Agent Context

## Key Files
{refs}

## API
- Search: https://search.codal.ir/api/search/
- Main: https://www.codal.ir/
- Excel: https://excel.codal.ir/service/Excel/

## Endpoints
{eps}

See references/*.md for full documentation.
"""
    for name in ["CLAUDE.md", ".cursorrules", ".opencode.md", ".windsurfrules", "CODIFY.md", ".github/copilot-instructions.md"]:
        p = ROOT / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    print(f"Generated {len(ENDPOINTS)}+ refs for Codal")

if __name__ == "__main__":
    generate()
