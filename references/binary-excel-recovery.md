# Binary Excel Recovery: Re-Downloading Corrupted Legacy Files

CODAL's Excel endpoint returns binary OLE2/BIFF `.xls` files for legacy reports (years 1391-1396, sometimes 1397). The standard pipeline corrupts these by calling `.decode("utf-8")` on the binary response. This reference covers how to re-download them properly.

## Overview

- **Files to recover:** ~1,209 across 328 stocks
- **Year range:** Mostly 1391-1396, some 1397
- **Server required:** Iran-based VPS
- **Expected time:** Hours (CODAL rate-limits aggressively)
- **API calls per file:** ~3 (get_fys → find_serial → download)

## Recovery Script

Two scripts needed on the server:

### Script 1: `recover_excel_v2.py` (the downloader)

```python
#!/usr/bin/env python3
"""
Efficient CODAL Excel recovery. Caches FY per stock.
Usage: cat targets.json | python3 recover_excel_v2.py
"""
import os, sys, json, re, time, urllib.request, urllib.parse

OUTPUT = "/tmp/codal_excel_fix"
os.makedirs(OUTPUT, exist_ok=True)
LOG = "/tmp/recover_v2.log"

DELAY = 6.0
BATCH_MAX = 999
COOLDOWN = 300
req_count = 0

HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json"}
HEADERS_BIN = {"User-Agent":"Mozilla/5.0"}

def log(msg):
    with open(LOG, 'a') as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

def rate_limit():
    global req_count
    req_count += 1
    if req_count > BATCH_MAX:
        log(f"  Cooldown {COOLDOWN}s...")
        time.sleep(COOLDOWN)
        req_count = 0
    time.sleep(DELAY)

def api_get(url, binary=False):
    rate_limit()
    h = HEADERS_BIN if binary else HEADERS
    for attempt in range(3):
        try:
            resp = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30)
            data = resp.read()
            return data if binary else data.decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                log(f"  429 — waiting 600s")
                time.sleep(600)
                req_count = 0
                continue
            return None
        except Exception:
            if attempt < 2: time.sleep(10)
            else: return None

fy_cache = {}
def get_fys(symbol):
    if symbol in fy_cache:
        return fy_cache[symbol]
    text = api_get(f"https://search.codal.ir/api/search/v1/financialYears?Symbol={urllib.parse.quote(symbol)}")
    try:
        fy_cache[symbol] = json.loads(text) if text else []
    except:
        fy_cache[symbol] = []
    return fy_cache[symbol]

serial_cache = {}
def find_serial(symbol, fy):
    key = f"{symbol}:{fy}"
    if key in serial_cache:
        return serial_cache[key]
    text = api_get(f"https://search.codal.ir/api/search/v2/q?Symbol={urllib.parse.quote(symbol)}&Category=1&Length=12&YearEndToDate={fy}&PageNumber=1&search=true")
    if not text:
        serial_cache[key] = None
        return None
    for letter in re.findall(r"<Letter[^>]*>(.*?)</Letter>", text, re.DOTALL):
        excel = re.search(r"<ExcelUrl[^>]*>([^<]*)</ExcelUrl>", letter)
        if excel:
            serial = excel.group(1).split("/GetAll/")[1].split("/")[0]
            serial_cache[key] = serial
            return serial
    serial_cache[key] = None
    return None

if __name__ == '__main__':
    targets = json.loads(sys.stdin.read())
    log(f"Starting recovery of {len(targets)} files")
    done = errors = 0
    for idx, (ticker, year, month, day, yk) in enumerate(targets):
        fname = f"{ticker}_{year}_{month}_{day}.xls"
        out_path = os.path.join(OUTPUT, fname)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            done += 1; continue
        fys = get_fys(ticker)
        match_fy = next((fy for fy in fys if fy.startswith(year)), None)
        if not match_fy: errors += 1; continue
        serial = find_serial(ticker, match_fy)
        if not serial: errors += 1; continue
        data = api_get(f"https://excel.codal.ir/service/Excel/GetAll/{serial}/0", binary=True)
        if not data or len(data) < 100: errors += 1; continue
        with open(out_path, 'wb') as f: f.write(data)
        done += 1
        if (idx+1) % 20 == 0:
            log(f"  {idx+1}/{len(targets)}: {done} OK, {errors} err")
    log(f"COMPLETE: {done} OK, {errors} errors")
    print(json.dumps({'done': done, 'errors': errors}))
```

### Script 2: Build target list (run on local machine)

```python
import os, json

raw_dir = 'data/codal/raw'
data_dir = 'data/codal'

targets = []
for d in sorted(os.listdir(raw_dir)):
    tdir = os.path.join(raw_dir, d)
    if not os.path.isdir(tdir): continue
    with open(os.path.join(data_dir, f'{d}.json')) as f:
        data = json.load(f)
    json_years = set(data.get('years', {}).keys())
    for f in sorted(os.listdir(tdir)):
        if not f.endswith('.html'): continue
        fp = os.path.join(tdir, f)
        with open(fp, 'rb') as fh:
            head = fh.read(200).decode('utf-8', errors='replace')
        if '<html' in head.lower() or '<table' in head.lower(): continue
        parts = f.replace('.html','').split('_')
        if len(parts) >= 4 and parts[1].isdigit():
            yk = f'{parts[1]}/{parts[2]}/{parts[3]}'
            if yk not in json_years:
                targets.append((d, parts[1], parts[2], parts[3], yk))

with open('/tmp/full_targets.json', 'w') as f:
    json.dump(targets, f)
print(f"Targets: {len(targets)}")
```

## Deployment Steps

### STARTING PARAMETERS (for Iran-based servers with strict rate limiting)

Some Iran-based servers have a particularly strict CODAL rate-limit tier. **DO NOT start with DELAY=1.5** — this triggers cascading 429s in minutes, locking the search API for hours. Use continuous-mode parameters from the start:

| Parameter | Value | Reason |
|-----------|-------|--------|
| `DELAY` | 6.0s | Keeps request rate below sliding-window threshold |
| `BATCH_MAX` | 999 | No artificial cooldown — continuous stream |
| `COOLDOWN` | 300s | Fallback only (rarely fires with BATCH_MAX=999) |

If you start with default values and see cascading `429 — waiting 600s` in the log, edit the script parameters in-place and restart:

```bash
ssh SERVER 'python3 -c "
p = \"/tmp/recover_excel_v2.py\"
c = open(p).read()
c = c.replace(\"DELAY = 1.5\", \"DELAY = 6.0\")
c = c.replace(\"BATCH_MAX = 30\", \"BATCH_MAX = 999\")
c = c.replace(\"COOLDOWN = 60\", \"COOLDOWN = 300\")
open(p, \"w\").write(c)
"'
screen -S codal_recovery -X quit
ssh SERVER 'screen -dmS excel_fix bash -c '\''python3 /tmp/recover_excel_v2.py < /tmp/full_targets.json 2>&1'\'''
```

### Actual Steps

```bash
# 0. Pre-flight: check if CODAL search API is already rate-limiting you
ssh SERVER 'curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  "https://search.codal.ir/api/search/v1/financialYears?Symbol=%D8%AE%DA%AF%D8%B3%D8%AA%D8%B1" \
  -H "Accept: application/json"'
# 429 = CODAL is blocking you. Wait 10-30 min before starting.
# 200 = OK to proceed.

# 1. Copy script and targets to server
scp recover_excel_v2.py ime:/tmp/
scp /tmp/full_targets.json ime:/tmp/

# 2. Start in screen session (survives SSH disconnect)
ssh SERVER "screen -dmS excel_fix bash -c 'python3 /tmp/recover_excel_v2.py < /tmp/full_targets.json 2>&1'"

# 3. Monitor progress
ssh SERVER "ls /tmp/codal_excel_fix/*.xls 2>/dev/null | wc -l"
ssh SERVER "tail -3 /tmp/recover_v2.log"

# 4. When done, rsync results back
rsync -avz ime:/tmp/codal_excel_fix/ /tmp/codal_excel_fix/
```

## Key Design Decisions

1. **FY caching** (`fy_cache` dict) — Avoids re-querying `financialYears` for every year of the same stock. The first call fetches all FYs for a ticker; subsequent years use the cache.

2. **Serial caching** (`serial_cache` dict) — Same serial is reused if the same stock+FY appears in multiple targets (doesn't happen with distinct years, but guards against duplicates).

3. **Binary-safe download** — `api_get(url, binary=True)` returns raw bytes without `.decode()`. The binary flag controls response handling.

4. **API rate limiting** — Same 30-request batch + 60s cooldown + 600s 429 backoff as the main pipeline. CODAL's rate limit applies to the entire `search.codal.ir` subdomain regardless of endpoint.

5. **Progress logging** — Writes to `/tmp/recover_v2.log` with timestamps, readable via `tail -f`.

## Post-Recovery: Parsing the Excel Files

After downloading the `.xls` files, parse with xlrd:

```python
import xlrd, os

wb = xlrd.open_workbook('/tmp/codal_excel_fix/فملی_1391_12_30.xls')
sh = wb.sheet_by_index(0)
print(f"Rows: {sh.nrows}, Cols: {sh.ncols}")
# Extract financial data — row labels are in Persian
# The xlrd structure is different from the HTML table structure
# Sheet usually has: row 0 = header, row 1+ = data rows
# Column structure varies by report year/company
```

## Cron Monitoring for Long-Running Recovery

Set up a cron job that checks the server every 15 minutes and reports to Telegram:

```bash
hermes cron create --schedule '*/15 * * * *' \
  --prompt "Check server for CODAL Excel recovery progress. Run: ls /tmp/codal_excel_fix/*.xls 2>/dev/null | wc -l and tail -5 /tmp/recover_v2.log. Report concise status." \
  --deliver telegram --name codal-excel-recovery
```

## Pitfalls

- **SSH ControlMaster issues** — SSH multiplexing can cause `exit code 255` on background commands. Use `ssh -o ControlMaster=no -o ControlPath=none SERVER 'command'` to bypass.
- **Cooldown stacking** — If the previous pipeline also ran on this server, CODAL may already be rate-limiting. Check `tail -f /tmp/recover_v2.log` after 5 minutes. If no progress, CODAL is likely still blocking from the previous run.
- **429 persistence** — CODAL's rate limit can persist for 10+ minutes. The 600s (10 min) backoff is appropriate.
- **Screen re-attach** — To see live output: `ssh SERVER 'screen -r codal_recovery'`. Detach with Ctrl+A, D.
