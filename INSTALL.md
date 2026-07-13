# Installation Guide — Codal Skill

## Hermes Agent
```bash
hermes skills tap add amirziveh/codal-skill
hermes skills install codal
skill_view(name="codal")
```

## Claude Code / Cursor / OpenCode / Windsurf
Open the project directory in the respective agent. Each auto-reads its config file.

## Python (stdlib only, no install)
```bash
cp templates/python-client.py my_project/
python3 my_project/codal_client.py
```

## Keeping updated
```bash
python3 generate-configs.py
```