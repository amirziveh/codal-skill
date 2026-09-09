#!/bin/bash
# CODAL Pipeline Progress Check — no_agent cron script
# Designed for use with `hermes cron create --no-agent --script codal-progress-check.sh`
# The script runs on a timer (e.g., every 15 min), SSHs into the PRIMARY remote server,
# counts done stocks and raw files, checks if the screen session is alive,
# reads the current stock number from the screen buffer, and computes ETA.
# With no_agent=True, stdout is delivered verbatim — no LLM tokens consumed.

REMOTE_HOST="PRIMARY_SERVER"
OUT_DIR="/tmp/codal_results"
SCREEN_NAME="codal_pipeline"
UNIVERSE_TOTAL=409

ssh "$REMOTE_HOST" "python3 -c '
import json, os, time, re, subprocess

OUT = \"'${OUT_DIR}'\"
UNIVERSE = '${UNIVERSE_TOTAL}'

files = sorted([f for f in os.listdir(OUT) if f.endswith(\".json\") and not f.startswith(\"_\")])
raw_dir = os.path.join(OUT, \"raw\")
raw_html = os.listdir(raw_dir) if os.path.isdir(raw_dir) else []

# Check pipeline running
r = subprocess.run([\"ps\", \"aux\"], capture_output=True, text=True)
running = \"${SCREEN_NAME}\" in r.stdout  # screen name appears in ps

# Aggregate
total_fy = 0
all_fys = set()
for fn in files:
    try:
        with open(os.path.join(OUT, fn)) as f:
            d = json.load(f)
            yrs = d.get(\"years\", {})
            total_fy += len(yrs)
            all_fys.update(yrs.keys())
    except Exception:
        pass

done = len(files)
now = time.strftime(\"%H:%M\")
bar_len = 20
pct = (done / UNIVERSE) * 100 if UNIVERSE else 0
filled = int(bar_len * pct / 100)
bar = \"█\" * filled + \"░\" * (bar_len - filled)

# ETA (rough: ~200s per stock including cooldowns)
remaining = UNIVERSE - done
eta_secs = remaining * 200
eta_h = eta_secs // 3600
eta_m = (eta_secs % 3600) // 60
eta_str = f\"~{eta_h}h{eta_m}m\" if eta_h else f\"~{eta_m}m\"

print(f\"📊 CODAL [{now}] {bar} {done}/{UNIVERSE} ({pct:.0f}%) — ETA {eta_str}\")
print(f\"• Stocks done: {done}")
print(f\"• FY records: {total_fy}")
print(f\"• Raw HTML files: {len(raw_html)}")
if all_fys:
    sorted_fys = sorted(all_fys)
    print(f\"• FY range: {sorted_fys[0][:7]}...{sorted_fys[-1][:7]} ({len(sorted_fys)} unique)\")

if not running:
    print(f\"⚠️  Pipeline NOT running! screen session \"${SCREEN_NAME}\" not found\")
else:
    # Read screen hardcopy for current stock
    scr = subprocess.run([\"screen\", \"-S\", \"${SCREEN_NAME}\", \"-X\", \"hardcopy\", \"/tmp/_codalscr.txt\"], capture_output=True)
    try:
        with open(\"/tmp/_codalscr.txt\", \"rb\") as f:
            raw = f.read()
        nums = re.findall(rb\"\\[(\\d+)\\]\", raw)
        if nums:
            latest = int(nums[-1].decode())
            stk = min(latest, UNIVERSE)
            print(f\"• Current: stock [{stk}/{UNIVERSE}]\")
            print(f\"• Rate: {done} stocks / ~{(done * 200 // 60)} min active\")
    except:
        print(\"• Screen log: unreadable\")
' 2>&1"
