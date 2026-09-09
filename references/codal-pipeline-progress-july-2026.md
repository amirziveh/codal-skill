# CODAL Pipeline Progress — Session Snapshot

## Fleet Status (Initial — Server 1 Offline)

Pipeline at **65.3%** (267/409 tickers). One server is completely offline for CODAL — no output directory, no monitoring script, no running pipeline process.

### Active Servers (4/5 reachable — 1 down)

| Server | Location | Access | Range | Stocks | FY Recs | HTML | Current | Status |
|--------|----------|--------|-------|--------|---------|------|---------|--------|
| Primary | Iran | Direct | 0-99 | **0** | **0** | **0** | — | ❌ DOWN |
| Server2 | Iran | Direct | 100-149 | 50 | 218 | 592 | [101] | ⏸ running |
| Server3 | Iran | Direct | 150-199 | 48 | 227 | 568 | [151] | ⏸ running |
| Server4 | Azerbaijan | JumpHost→Primary | 200-304 | 83 | 349 | 952 | [201] | ✅ done |
| Server5 | Azerbaijan | Direct | 305-408 | 86 | 487 | 867 | [306] | ✅ done |
| **Total** | | | | **267** | **1,281** | **2,979** | | ~3m ETA |

### Local Backup (synced from 4 running servers)
- 362 JSON files
- 4,001 raw HTML files
- Location: Local data directory

## Fleet Status (After Recovery — All 5 Servers Running)

All 5 servers are now running with clean output directories. Issues fixed:
- **Primary**: monitoring script deployed, pipeline switched to continuous mode (DELAY=5s, BATCH_MAX=999), reduced FYs to 10/stock — now running at ~3 stocks/5min with zero 429s
- **Server4**: 111 stale files from previous larger universe cleaned, pipeline restarted with correct 55-stock range
- **Server5**: 50 stale files cleaned, pipeline restarted with correct 54-stock range
- **Server2 & Server3**: Already healthy with original batch-cooldown settings

Current state (~06:00 UTC):
| Server | Range | Stocks | FY Recs | HTML | Status |
|--------|-------|--------|---------|------|--------|
| Primary | 0-99 | ~62 | ~292 | ~522 | ✅ running (continuous mode) |
| Server2 | 100-199 | ~76 | ~347 | ~907 | ✅ running (batch mode) |
| Server3 | 200-299 | ~74 | ~336 | ~873 | ✅ running (batch mode) |
| Server4 | 300-354 | ~1 | ~5 | ~23 | ✅ running (continuous mode, just restarted) |
| Server5 | 355-408 | 0 | 0 | 0 | ✅ running (continuous mode, just restarted) |

All ranges now use the correct universe sizes: Primary=100, Server2=100, Server3=100, Server4=55, Server5=54 (total 409).

### Known Issues

**❌ Primary server offline (stocks 0-99 unprocessed)**
- No output directory — completely missing
- No monitoring script — can't check status
- Pipeline script exists but was never deployed to `/tmp/` and started
- **To fix**: Deploy the pipeline script, status script, then start in screen:
  ```bash
  cp PIPELINE_SCRIPT /tmp/
  screen -dmSL codal_pipeline python3 /tmp/PIPELINE_SCRIPT 100 0
  ```

### Prior Session (Range Overlap Fix)

Previous session recovered from a range overlap bug where the primary server was running without args (processing all 409 stocks instead of 0-99). Fixed by killing the unbounded screen and restarting with explicit `100 0`. At that point all 5 servers were running with corrected ranges and ~14h ETA.

### Quick Check Commands

```bash
# Primary (local host — will fail if pipeline not deployed)
ssh PRIMARY_SERVER 'python3 /tmp/status_script.py'
# Remote servers
ssh SERVER2 'python3 /tmp/status_script.py'
ssh SERVER3 'python3 /tmp/status_script.py'
ssh SERVER4 'python3 /tmp/status_script.py'
ssh SERVER5 'python3 /tmp/status_script.py'

# Check if primary has pipeline deployed
ssh PRIMARY_SERVER 'ls /tmp/status_script.py /tmp/codal_results 2>&1; ps aux | grep codal | grep -v grep'
```

### Stock Universe Ranges (disjoint, zero overlap)

- Primary: 0-99 (0 of 100 done — ❌ offline)
- Server2: 100-149 (50 of 50 done ✅)
- Server3: 150-199 (48 of 50 done, ~2 remaining)
- Server4: 200-304 (83 of 105 done ✅)
- Server5: 305-408 (86 of 104 done ✅)

Total: 409 stocks, all ranges covered in theory, but Primary's slice is entirely unprocessed.
