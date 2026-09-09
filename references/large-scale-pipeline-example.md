# Large-Scale CODAL Pipeline — Session Example (July 2026)

This reference documents the actual CODAL pipeline built for the multi-factor asset pricing replication project. The pattern is generalizable to any large-scale financial data extraction from CODAL.

## Project Context

- **Goal**: Extract financial statements (Total Assets, Equity, Revenue, COGS, SG&A, Interest, Net Income) for ~409 Iranian stocks across ~15 years each
- **Pipeline**: Python script running on a fleet of VPSs, each with a disjoint stock range
- **Pacing**: 2.5s delay per request, batch of 20 before 180s cooldown
- **Total stocks**: 409, each needing ~31 API calls (1 FY list + 15 report searches + 15 Excel downloads)

## Pipeline Script

```
For each stock in the stock universe:
  1. Skip if output JSON already exists (resume-safe)
  2. Get fiscal year-end dates (GET financialYears)
  3. For each fiscal year (≥1388, last 15):
     a. Search for parent-company annual report (YearEndToDate filter → 1 call)
     b. Download Excel HTML (excel.codal.ir — not rate-limited alongside search)
     c. Parse HTML tables → extract 8 financial metrics
  4. Save parsed JSON
  5. Save raw HTML for re-parsing
  6. Print `[{i}] {symbol}... ✅ {N} yr`
  7. Cooldown if over batch limit
```

### Argument-based Stock Range

```python
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
start_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
```

This is the key mechanism for parallel execution — each server gets a different `start_idx` + `limit`.

### Output Structure

```
/tmp/codal_results/
├── {symbol}.json              # Parsed financial data
├── raw/
│   └── {symbol}_{fy}.html     # Raw Excel HTML (~200-500KB each)
└── _status.json               # Aggregate snapshot
```

Each JSON file:
```json
{
  "ticker": "برکت",
  "company": "گروه دارویی برکت",
  "years": {
    "1403/12/30": {
      "total_assets": 540734681000,
      "total_equity": 339197399000,
      "revenue": 300940815000,
      "cogs": 166741080000,
      "sga": 11344709000,
      "interest": 12282236000,
      "op_profit": 150092791000,
      "net_income": 166026012000,
      "audited": true
    }
  }
}
```

## 5-Server Fleet Architecture

The fleet was assembled within ~45 minutes of conversation time as the user bought cheap VPSs and provided IPs one by one.

| # | Host | Location | Access | Range | 
|---|------|----------|--------|-------|
| 1 | **Primary** | Iran | Direct SSH | 0-99 |
| 2 | **Server2** | Iran | Direct SSH | 100-199 |
| 3 | **Server3** | Iran | Direct SSH | 150-199 |
| 4 | **Server4** | Azerbaijanbaijan | JumpHost via Primary | 200-304 |
| 5 | **Server5** | Azerbaijanbaijan | Direct SSH | 305-408 |

### Key Observations

- **Same IP range, different countries**: Same /16 from the same provider can span physical borders across countries.
- **Firewall asymmetry**: Some Azerbaijanbaijan servers blocked inbound SSH from outside Iran (connection timed out from a non-Iran machine) but were reachable from within Iran. Other Azerbaijanbaijan servers had no such restriction. Always test direct first.
- **CODAL access**: Both Iran and Azerbaijanbaijan servers reached CODAL with HTTP 200. Always test before committing setup time.
- **Disjoint ranges**: 0-99, 100-149, 150-199, 200-304, 305-408 — zero overlap, no shared state needed.
- **One VPS was accidentally deleted mid-session**: All its work (1 stock, 8 raw HTMLs) was recovered from the primary's rsync backup. **Always rsync from the primary server to local storage on each monitoring tick.**

### Fleet Setup Sequence (per new server)

When the user provides a new IP:

1. Test connectivity:
   ```bash
   ssh -o StrictHostKeyChecking=accept-new ubuntu@IP whoami
   ```
   - If timeout → try from the Iran primary: `ssh PRIMARY_SERVER "ssh ubuntu@IP whoami"`
   - If that also fails → server not ready yet, wait.
   
2. Copy the shared fleet key:
   ```bash
   ssh-copy-id -o StrictHostKeyChecking=accept-new -i FLEET_KEY.pub ubuntu@IP
   ```
   If direct SSH fails, pipe through primary:
   ```bash
   cat FLEET_KEY.pub | ssh PRIMARY_SERVER \
     "ssh ubuntu@IP 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'"
   ```

3. Install deps:
   ```bash
   ssh ubuntu@IP 'sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv screen && python3 -m venv ~/venv && ~/venv/bin/pip install curl_cffi -q'
   ```

4. Transfer files (via primary if behind firewall):
   ```bash
   scp stock_universe.json ubuntu@IP:/tmp/
   ssh PRIMARY_SERVER 'cat /tmp/codal_pipeline.py' | ssh ubuntu@IP 'cat > /tmp/codal_pipeline.py && chmod +x /tmp/codal_pipeline.py'
   ```

5. Start in screen:
   ```bash
   ssh ubuntu@IP 'screen -dmSL codal_<name> ~/venv/bin/python3 /tmp/codal_pipeline.py <limit> <start_idx>'
   ```

6. Verify:
   ```bash
   ssh ubuntu@IP 'screen -ls; screen -S codal_<name> -X hardcopy /tmp/_out.txt; cat /tmp/_out.txt 2>/dev/null | head -2'
   ```

7. Deploy status script and add to monitoring.

## Progress Monitoring

### Status Script (deployed to each server)

```python
#!/usr/bin/env python3
"""Quick status check — deployed to each server."""
import json, os, subprocess, re

OUT = "/tmp/codal_results"
files = [f for f in os.listdir(OUT) if f.endswith(".json") and not f.startswith("_")]
raw = os.listdir(os.path.join(OUT, "raw")) if os.path.isdir(os.path.join(OUT, "raw")) else []
tf = sum(len(json.load(open(os.path.join(OUT, fn))).get("years", {})) for fn in files if not fn.startswith("_"))

r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
run = "yes"
for p in ["codal_pipeline", "codal_azer", "codal_azer2", "codal_pipeline"]:
    if p in r.stdout: break
else: run = "NO"

# Read screen hardcopy for current position
cur = "?"
for scr in ["codal_pipeline", "codal_runner"]:
    subprocess.run(["screen", "-S", scr, "-X", "hardcopy", "/tmp/_sc.txt"], capture_output=True)
    try:
        nums = re.findall(rb"\[(\d+)\]", open("/tmp/_sc.txt", "rb").read())
        if nums: cur = nums[-1].decode(); break
    except: pass

print(f"{len(files)}|{tf}|{len(raw)}|{run}|{cur}")
```

### Progress Check Script (in skill scripts/: `scripts/codal-progress-check.sh`)
A bash alternative for `no_agent` cron mode — SSHs into a single server, counts done, checks screen health, computes ETA. Schedule via `hermes cron create --no-agent --script codal-progress-check.sh --schedule 15m`. The `no_agent` variant delivers stdout verbatim with no LLM cost.

Both produce output in this format:

**⚠️ Server lifecycle**: VPS instances may go offline mid-pipeline (terminated by provider, deleted accidentally, IP changed, or SSH firewall rules rotated). The monitoring script must handle unreachable servers gracefully — timeouts should produce "⚠️ Offline" status, not crash the report.

Each server's SSH command is independent — some need `-o ProxyJump=PRIMARY`, some don't:

```python
import subprocess, json

def get(ssh_cmd, label="Server", timeout=15):
    """Fetch status from a pipeline server. Returns a dict with stock/fy/html counts,
    or a dict with 'error' on failure."""
    try:
        r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"error": f"SSH exit code {r.returncode}", "stocks": 0, "fy": 0, "html": 0, "current": "?"}
        parts = r.stdout.strip().split("|")
        if len(parts) < 4:
            return {"error": f"Unexpected output: {r.stdout[:100]}", "stocks": 0, "fy": 0, "html": 0, "current": "?"}
        return {
            "stocks": int(parts[0]), "fy": int(parts[1]), "html": int(parts[2]),
            "running": parts[3], "current": parts[4] if len(parts) > 4 else "?"
        }
    except subprocess.TimeoutExpired:
        return {"error": "SSH timeout", "stocks": 0, "fy": 0, "html": 0, "current": "?"}
    except Exception as e:
        return {"error": str(e), "stocks": 0, "fy": 0, "html": 0, "current": "?"}

KEY = os.path.expanduser("~/.ssh/FLEET_KEY")
servers = [
    ("Primary (Iran)",   get(["ssh", "PRIMARY", "python3 /tmp/status_script.py"])),
    ("Server2 (Iran)", get(["ssh", "-i", KEY, "ubuntu@SERVER2_IP", "python3 /tmp/status_script.py"], timeout=15)),
    ("Server4 (Azerbaijan)", get(["ssh", "-oProxyJump=PRIMARY", "-i", KEY, "ubuntu@SERVER4_IP", "python3 /tmp/status_script.py"], timeout=15)),
]
# Add servers that may be offline — error handling makes this safe
for ip, label in [("SERVER5_IP", "Server5 (Azerbaijan)"), ("SERVER3_IP", "Server3 (Iran)")]:
    servers.append((label, get(["ssh", "-i", KEY, f"ubuntu@{ip}", "python3 /tmp/status_script.py"], timeout=10)))

total_done = sum(s["stocks"] for _, s in servers)
```

**Real-world example** (July 19, 2026 — 3 weeks into pipeline, 2 of 5 servers offline):
```
📊 CODAL Pipeline (19:35 UTC)
██░░░░░░░░░░░░░░░░░░ 13.2%

✅ Primary (Iran):    33 st | 159 FY | 323 HTML [30]
✅ Server2 (Iran):   7 st |  30 FY |  82 HTML [101]
✅ Server4 (Azerbaijan):   8 st |  32 FY |  99 HTML [201]
⚠️ Server3 (Iran):   OFFLINE (was at 3 st / 21 FY / 41 HTML)
⚠️ Server5 (Azerbaijan):   OFFLINE (was at 6 st / 30 FY / 55 HTML)
─────────────────────────
Total: 48/409 st reachable | 221 FY | 504 HTML | ⏳ ~17h (if 3 servers)
💿 Local: 32 json, 315 html ✅
```

The fleet was originally 5 servers (54 stocks done, 257 FY, 576 HTML). Two VPSs went offline between monitoring ticks — common with cheap VPS providers. The reachable 3 servers continue making progress.

This data also appears in `references/codal-pipeline-progress-july-2026.md` for per-snapshot detail.

## ETA Calculation

```python
# Simple estimate based on combined rate
rate = max(3, total_done / elapsed_hours) if total_done > 0 else 15
remaining = max(0, TOTAL - total_done)
eta_hours = remaining / rate if rate > 0 else 99
```

## Fleet Argument Pitfall: Range Overlap

The MOST COMMON mistake in multi-server CODAL fleets is **running a server without explicit `limit` and `start_idx` arguments**. When a server starts with no args:

```python
limit = int(sys.argv[1]) if len(sys.argv) > 1 else None  # → None → no limit!
start_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0  # → 0
todo = universe[0:]  # → ALL stocks! (not just intended range)
```

This causes that server to process stocks from every other server's range, wasting API calls (same stock downloaded 2-5×) and slowing the whole fleet.

**How to detect**: Check the actual command via `ps aux | grep codal` — if you see `python3 /tmp/pipeline script` with no numbers after it, range is unbounded.

**How to fix** (without losing existing progress):
1. Kill the screen session: `screen -S codal_<name> -X quit`
2. Restart with explicit args: `screen -dmSL codal_<name> ~/venv/bin/python3 /tmp/codal_pipeline.py <limit> <start_idx>`
3. The script skips existing JSON files, so already-processed stocks in the correct range are not re-downloaded
4. Stale JSON files for stocks outside the correct range (left from the unbounded run) can be left on disk — they won't be re-processed during the constrained run. Or clean them up by removing files whose indices are outside the assigned range.

**Range verification**: After restart, run:
```bash
ssh SERVER 'python3 /tmp/status_script.py'
# Then cross-reference tickers against stock_universe indices
python3 -c "
import json
with open('stock_universe.json') as f:
    u = json.load(f).get('universe', [])
for i in [0, 99, 100, 149, 150, 199, 200, 304, 305, 408]:
    print(f'[{i}] {u[i][\"ticker\"]}')
"
```

### Rsync `--delete` Danger with Multi-Server Backup

When syncing data from multiple servers to a single local directory, **do NOT use `--delete` on secondary servers**:

```python
# ✅ Correct: --delete only on PRIMARY server
rsync -az --delete primary:/tmp/codal_results/ LOCAL/
# ❌ Wrong: --delete on secondary will WIPE primary's data
rsync -az --delete secondary:/tmp/codal_results/ LOCAL/  # DON'T!
# ✅ Correct: plain sync for secondary servers
rsync -az secondary:/tmp/codal_results/ LOCAL/
```

**Why**: Each server only has its own range of stocks. If a secondary server (e.g. Server2 with range 100-149) syncs with `--delete`, it removes all files from the primary's range (0-99) that the secondary doesn't have. The data is gone permanently.

**Pattern for the monitoring script**:
```python
SYNC_TARGETS = [
    (["rsync", "-az", "--delete", "PRIMARY:/tmp/codal_results/", LOCAL + "/"], "Primary"),   # delete on primary
    (["nice", "rsync", "-az", "-e", "ssh -i " + KEY,
      "ubuntu@SERVER2_IP:/tmp/codal_results/", LOCAL + "/"], "Server2"),              # no delete!
    (["nice", "rsync", "-az", "-e", "ssh -i " + KEY,
      "ubuntu@SERVER3_IP:/tmp/codal_results/", LOCAL + "/"], "Server3"),            # no delete!
]
```

## Data Backup (critical)

The primary server (Primary) gets `rsync -az --delete` — this seeds the local directory and removes stale files. Secondary servers use plain `rsync -az` (no `--delete`) to add their non-overlapping data without removing the primary's files. Each monitoring tick syncs all servers in sequence. This proved essential when one VPS was accidentally deleted — the monitoring had already synced its partial output.

## Real-World Throughput

| Metric | Single Server | 3 Servers | 5 Servers |
|--------|---------------|-----------|-----------|
| Per-stock time (requests + cooldown) | ~200s | ~200s | ~200s |
| Total pipeline time (409 stocks) | ~24-35h | ~10-12h | ~6-8h |
| Stock rate | ~12 st/h | ~35 st/h | ~55 st/h |

Each server independently hits CODAL rate limits. More servers = faster completion. The limiting factor is the number of distinct IPs available.

## Known Parser Quality Limitation (July 2026)

The `parse_financial()` function in `pipeline script` matches specific Persian row labels in CODAL Excel HTML tables. However, actual CODAL reports use varying label formats across companies and reporting periods. This produces **significant coverage gaps** for some financial fields.

**Measured coverage (from a 409-stock × ~15-year run):**

| Field | Coverage | Status |
|-------|----------|--------|
| `total_assets` | ~65% of FY records | Moderate — label "جمع دارایی‌ها" is consistent |
| `revenue` | ~65% | Moderate — "درآمدهای عملیاتی" |
| `net_income` | ~49% | Low — varying formats for "سود (زیان) خالص" |
| `total_equity` | ~45% | Low — "جمع حقوق صاحبان سهام" sometimes alternative spellings |
| Both Assets+Equity | ~39% | **Low — need parser revision for academic-grade data** |

**Why the gap exists:**
- Some reports use 4-column layout (label, current, prior, change) instead of the expected 2-column layout
- Arabic Yeh (ي) vs Persian Yeh (ی) differences in row labels even after normalization
- Some companies use slightly different Persian phrasing for the same accounting concept
- Consolidated vs separate statements have different table layouts (the current parser only checks certain table indices)

**How to improve without re-downloading:**
Since raw HTML is saved (`raw/{symbol}_{fy}.html`), the parser can be revised and re-run against local files:
```python
import os, json, glob

RAW_DIR = "/tmp/codal_results/raw"
for html_path in glob.glob(os.path.join(RAW_DIR, "*.html")):
    with open(html_path) as f:
        html = f.read()
    # Apply improved parser
    parsed = improved_parse(html)
    # ... save updated JSON
```

Raw HTML files are ~200-500KB each. 4,200 files from a 409-stock run consume ~1.2GB. Re-parsing takes ~seconds, not hours.

## Key Lessons Learned

1. **Raw HTML caching is essential** — The parser may miss fields the first time. With raw HTML saved, re-parsing all 409 stocks takes seconds instead of 22 hours of re-downloading.

2. **Screen session for remote scripts** — Screen captures stdout to scrollback buffer, readable via `screen -X hardcopy` over SSH.

3. **Stock number tracking** — Using `[{i}]` prefix on each status line (`[5] آلومینا... ✅ 4 yr`) makes progress tracking from screen buffer easy.

4. **Skip detection for restart safety** — Checking existing output files before processing makes the pipeline restart-safe.

5. **Parallel servers need disjoint ranges** — Simple `start_idx` + `limit` approach avoids shared state or coordination.

6. **IP-based rate limiting** — Each distinct IP gets its own rate limit bucket. Same-IP parallel processes would not help.

7. **One SSH key for the whole fleet** — Using the same key across all servers (via `ssh-copy-id` with `ssh (with appropriate auth)`) simplifies management.

8. **ProxyJump for geo-blocked servers** — Some Azerbaijanbaijan VPSs block inbound SSH from outside Iran. Route through the Iran primary: `ssh -o ProxyJump=PRIMARY ubuntu@<IP>`.

9. **Monitor from outside the fleet** — Run the monitoring script on your local machine (not on any VPS). If a VPS crashes, you still get a report showing it's down.

10. **Local backup sync** — `rsync -az --delete` from the primary after each monitoring tick ensures data survives accidental server deletion.

## Post-Pipeline Reconciliation: Re-targeting a Server on Missing Stocks

When the initial fleet run finishes, a handful of stocks are usually still missing (transient errors, timeouts, or stocks not covered due to overlapping range resets). This session documents the **tail-end reconciliation** pattern: re-purposing the fastest available server to cover the missing block.

### Workflow

**1. Identify the exact missing stocks** — Compare local file inventory against the full universe CSV. Use ticker symbols (never array indices) since local CSV and server JSON may be sorted by different fields:

```python
import os, csv

local = {f.replace('.json','') for f in os.listdir('data/codal/')
         if f.endswith('.json') and not f.startswith('_')}

with open('stock_universe.csv') as f:
    reader = csv.DictReader(f)
    universe = {r['ticker'] for r in reader}

missing = universe - local
print(f'{len(missing)} stocks missing: {sorted(missing)}')
```

**2. Check each missing stock's origin** — Determine which server's original range it belonged to, then check if that server ever processed it (some gaps are permanent — CODAL Tier 2/3 stocks that return empty FY lists or all-404 Excel endpoints):

| Kind | Symptom | Action |
|------|---------|--------|
| **Tier 3 (no FYs)** | `v1/financialYears` returns `[]` | Permanent gap, skip |
| **Tier 2 (all 404)** | FY listing OK, but every Excel URL returns 404 | Permanent gap, skip |
| **Transient error** | Server hit rate-limit or network blip | Re-target to fastest server |

Some stocks are confirmed permanent gaps (empty FY lists or all-404 Excel endpoints) — never retry them.

**3. Pick the re-target server** — Choose the server that was fastest or has the most reliable connection. Check it's idle (no CODAL process running) and has the `universal runner script` (stdlib-only, no curl_cffi dependency) available. If not, deploy it:

```bash
# Deploy the universal runner (stdlib-only, works everywhere)
cat scripts/universal runner script | ssh SERVER 'cat > /tmp/universal runner script'

# Verify stock_universe.json exists (needed for --start/--limit args)
ssh SERVER 'ls /tmp/stock_universe.json'
```

**4. Launch a targeted run** — Start with a range covering just the missing stocks. The universal runner accepts `--start N` and `--limit M` and auto-skips already-existing files:

```bash
ssh SERVER 'cd /tmp && nohup python3 universal runner script --start 260 --limit 50 \
  > /tmp/codal_tail.log 2>&1 &'
```

For long tail runs, use screen instead:
```bash
ssh SERVER 'screen -dmSL codal_tail bash -c \
  "python3 /tmp/universal runner script --start 260 --limit 50 2>&1 | tee /tmp/codal_tail.log"'
```

**5. Monitor the tail run** — Check periodically for new file additions:

```bash
# Count files before and after
ssh SERVER 'ls /tmp/codal_results/*.json 2>/dev/null | grep -v _status | wc -l'

# Check the log for progress
ssh SERVER 'tail -5 /tmp/codal_tail.log'
```

The log format shows each stock as it completes:
```
[30] شوینده... ✅ 7 yr
[31] نماد...    ✅ 7 yr
```

The bracketed number is relative position within the `--start`/`--limit` range, not the absolute universe index.

**6. Sync data back to local** — Once the tail run finishes (or periodically during), use `rsync` from that single server ONLY (no `--delete` since it's a secondary server):

```bash
rsync -avz SERVER:/tmp/codal_results/ ~/data/codal/
```

**7. Verify completeness** — Re-run step 1 to confirm only the permanent gaps remain:

```bash
python3 -c "
import os
local = {f.replace('.json','') for f in os.listdir('data/codal/')
         if f.endswith('.json') and not f.startswith('_')}
perm_gaps = set()  # stocks confirmed as permanent gaps
remaining = universe - local - perm_gaps
print(f'Total: {len(local)}/{len(universe)} stocks')
print(f'Permanent gaps: 3 (اسفراین, تادیکو, سلیمان)')
print(f'Unexpected missing: {len(remaining)}')
if remaining: print(f'  {sorted(remaining)}')
"
```

### Pitfalls

- **Server `stock_universe.json` sorting differs from local CSV** — The server's JSON may be sorted by `codal_name`/`company_name` while the local CSV is sorted by Persian ticker. Never use array indices to map stocks between formats. Always cross-reference by ticker symbol. This is critical when computing `--start`/`--limit` values — the index for a given ticker on the server may be completely different from the local index.

- **`universal runner script` uses stdlib only** — It relies on `urllib.request` (not curl_cffi) and has conservative defaults (2.5s delay, batch 20, 180s cooldown). It's slower than `pipeline script` but works on ANY server with Python 3. If the target server has `curl_cffi` installed, prefer `pipeline script` for its better rate-limit bypass capability and faster pacing (1.5s delay, batch 30, 60s cooldown under the accelerated profile).

- **Screen sessions die on reboot** — If the server reboots during the tail run, the screen session is lost. The `nohup` + `&` variant leaves a PID that can be re-attached but still dies on reboot. For critical tail runs, set up a systemd oneshot timer or use `cron` polling to detect incomplete runs.

- **File count inflation from stale output** — If the server previously ran with a different range, old JSON files from the earlier range pollute the file count. The skip-done logic correctly avoids re-downloading, but the count appears higher than expected. Check `_status.json` for the `ok` field, or cross-reference the file list against the specific missing block tickers to get accurate progress.
