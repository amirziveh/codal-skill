# Codal Skill — Iranian Corporate Disclosure Data for AI Agents

[![GitHub](https://img.shields.io/badge/agent-hermes_%7C_claude_%7C_cursor_%7C_opencode_%7C_copilot_%7C_windsurf-blue)](https://github.com/amirziveh/codal-skill)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/amirziveh/codal-skill)](https://github.com/amirziveh/codal-skill/commits)

A universal, reverse-engineered API reference for **Codal (codal.ir)** — the official electronic disclosure system of the Iranian capital market. **Works natively with every major AI coding agent** — no plugins, no SDKs, just markdown.

Covers the **search API**, **reference data** (5,387 companies, 72 industry groups, ~100 letter types), and **report downloads** (PDF, Excel, HTML).

## What's inside

| Directory | Contents | Any agent? |
|-----------|----------|-----------|
| `references/` | API endpoint catalog, complete letter type taxonomy | ✅ Yes — plain markdown |
| `templates/` | Python client (stdlib-only, 40+ methods) | ✅ Yes — plain code |
| `SKILL.md` | Hermes Agent skill | ✅ Hermes |
| `CLAUDE.md` | Claude Code project hook | ✅ Claude Code |
| `.cursorrules` | Cursor AI project hook | ✅ Cursor |
| `.opencode.md` | OpenCode project hook | ✅ OpenCode |
| `.windsurfrules` | Windsurf project hook | ✅ Windsurf |
| `.github/copilot-instructions.md` | GitHub Copilot | ✅ Copilot |
| `generate-configs.py` | Auto-generates all agent hooks | ✅ Developer tool |

## Quick start

### Any AI agent
Open the project directory — your agent auto-detects its config file.

### Hermes Agent
```bash
hermes skills tap add amirziveh/codal-skill
hermes skills install codal
```

### Python (any environment)
```python
from python_client import CodalClient

client = CodalClient()
letters = client.search(symbol="فولاد", length=5)
for l in letters:
    print(f"[{l['TracingNo']}] {l['Title'][:60]}")
```

## API

| Endpoint | Description |
|----------|-------------|
| `search.codal.ir/api/search/v1/companies` | All 5,387 companies |
| `search.codal.ir/api/search/v1/categories` | Letter type taxonomy ~100 types |
| `search.codal.ir/api/search/v2/q?Symbol=...` | Search filings by symbol |

## License

MIT — free to use, modify, and distribute. All data is from public APIs of Codal (codal.ir).
