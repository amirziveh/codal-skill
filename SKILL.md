---
name: codal
description: "Work with Codal (codal.ir) — the official Iranian corporate disclosure system. Search financial statements, auditor reports, board decisions, and other mandatory filings by Iran's capital market companies. Covers the search API, reference data, report detail pages, and file downloads."
version: 1.10.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [codal, iran, financial-disclosure, corporate-reporting, financial-statements, auditor, capital-market, iranian-companies]
---

# Codal — Iranian Corporate Disclosure API

Use this skill when working with **Codal (codal.ir)** — the official electronic disclosure system of the Iranian capital market. All publicly traded companies in Iran (Bourse, Fara Bourse, Payeh) publish their financial statements, auditor reports, board decisions, and other mandatory disclosures here.

## When to use

- Search for **financial statements** (صورت‌های مالی) of Iranian companies
- Find **auditor reports** (گزارش حسابرس) and audit opinions
- Look up **board decisions** (تصمیمات هیئت مدیره), **EPS forecasts** (پیش‌بینی درآمد هر سهم)
- Get **monthly activity reports** (گزارش فعالیت ماهانه)
- Download **PDF or Excel** versions of financial reports
- Get **company reference data** (symbols, ISIC codes, industry groups)
- Search for **specific letter types** (e.g., capital increase announcements, shareholder meeting notices)

## Key Concepts

### Architecture

Codal is an ASP.NET WebForms application with an AngularJS SPA frontend and a separate REST API for search:

| Component | URL | Purpose |
|-----------|-----|---------|
| **Search API** | `https://search.codal.ir/api/search/` | REST API — content negotiation (JSON with `Accept: application/json`, see API Response Format below) |
| **Main Site** | `https://www.codal.ir/` | ASP.NET WebForms site |
| **Excel Service** | `https://excel.codal.ir/service/Excel/` | Excel file downloads |
| **DDoS Protection** | `https://www.codal.ir/api/ddos/v1/` | Captcha service (rate limit protection) |

### Geo-restriction

Codal.ir is geo-restricted and only accessible from inside Iran. All API calls must be routed through an Iran-based server. The `search.codal.ir` subdomain is also geo-restricted.

### Letter Serial

Every filing (letter) has a unique **LetterSerial** — a base64-like opaque string used to access the report page, PDF, Excel, and attachments (e.g. `VmoA3IWcyPnuPOmTzoJjaA%3d%3d`).

**⚠️ No direct mapping from TracingNo → LetterSerial** exists outside the CODAL search API. The TSETMC Codal proxy (`GetPreparedDataByInsCode`) returns TracingNo but NOT LetterSerial. To get the Excel data, you still need the CODAL search API or to construct the URL through CODAL's website.

### Excel Format: HTML Tables (Modern) + Binary OLE2 (Legacy)

The CODAL "Excel" download at `excel.codal.ir/service/Excel/GetAll/{serial}/0` returns **two different formats depending on the report's age:**

**Modern reports (years 1397+):** HTML tables in Microsoft Office HTML format. The response has `Content-Type: text/html` with 200-500KB of table markup. Financial data is contained within `<table>` elements. This is the standard format documented below.

**Legacy reports (years 1391-1396):** Binary OLE2 (BIFF) `.xls` files — actual binary Excel documents. These MUST NOT be decoded as UTF-8 text. If decoded, non-UTF-8 bytes get replaced with U+FFFD, permanently corrupting the file.

**⚠️ CRITICAL: `.decode("utf-8")` destroys legacy Excel files.** The pipeline's `rate_limited_get` calls `resp.read().decode("utf-8")` on all responses. For legacy binary Excel, every non-UTF-8 byte is replaced with `\uFFFD`. The OLE2 signature `D0CF11E0` becomes `EFBFBD EFBFBD 11E0`. **6,044 corrupted byte groups per 82KB file** observed. These are permanently unreadable.

**Detection:**
```python
def is_binary_excel(fp):
    with open(fp, 'rb') as f:
        head = f.read(200).decode('utf-8', errors='replace')
    if '<html' in head.lower() or '<table' in head.lower() or '<!DOCTYPE' in head.lower():
        return False
    return True
```

**Year distribution (observed):** 1391-1396 = 0-5% HTML, 1397 = 82% HTML, 1398+ = 99-100% HTML.

**Recovery:** Re-download with binary-safe handler — `resp.read()` (no `.decode()`), save as `.xls`, parse with `xlrd`.

**Table index structure** (verified on consolidated audited reports):
| Table | Content | Key Row Labels |
|-------|---------|----------------|
| 0 | Consolidated Balance Sheet | "جمع دارایی‌ها" (Total Assets), "جمع حقوق صاحبان سهام" (Total Equity) |
| 2 | Consolidated Income Statement | "درآمدهای عملیاتی" (Revenue), "بهای تمام شده..." (COGS), "هزینه‌های فروش، اداری و عمومی" (SG&A), "هزینه‌های مالی" (Interest) |
| 4 | Consolidated Cash Flow | — |
| 5 | Separate Balance Sheet | Same labels, parent-only figures |
| 7 | Separate Income Statement | Same labels, parent-only figures |

**Row format**: 4 columns for single-column tables (label, current_year, prior_year, change%), 8 columns for dual-column tables (left_label, left_cur, left_prev, left_chg%, right_label, right_cur, right_prev, right_chg%).

**Persian number parsing**: Numbers use Persian digits (۰۱۲۳۴۵۶۷۸۹) with comma thousand separators and parentheses for negatives (e.g., `(۱۶۶,۷۴۱,۰۸۰)`). Convert using `str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")` and remove commas.

### TracingNo

Each filing also has a numeric **TracingNo** (پیگیری) — a unique integer identifier (e.g. `1563609`).

### Dates

All dates in the Codal API are **Jalali (Persian) strings** in `YYYY/MM/DD HH:MM:SS` format (e.g. `1405/04/22 12:26:31`). For date-only fields, the format is `YYYY/MM/DD` (e.g. `1404/12/29`).

### Company State Codes

| Code | Meaning |
|------|---------|
| -1 | همه موارد (All) |
| 0 | پذیرفته شده در بورس تهران (Bourse) |
| 1 | پذیرفته شده در فرابورس ایران (Fara Bourse) |
| 2 | ثبت شده پذیرفته نشده (Registered, not accepted) |
| 3 | ثبت نشده نزد سازمان (Not registered with SEO) |
| 4 | پذیرفته شده در بورس کالای ایران (IME) |
| 5 | پذیرفته شده در بورس انرژی ایران (Energy Exchange) |

### Reporting Type Codes

| Code | Meaning |
|------|---------|
| -1 | همه موارد (All) |
| 1000000 | تولیدی (Manufacturing) |
| 1000001 | ساختمانی (Construction) |
| 1000002 | سرمایه گذاری (Investment) |
| 1000003 | بانک (Bank) |
| 1000004 | لیزینگ (Leasing) |
| 1000005 | خدماتی (Services) |
| 1000006 | بیمه (Insurance) |
| 1000007 | حمل و نقل دریایی (Maritime Transport) |

## API Endpoints

### Base URL: `https://search.codal.ir/api/search/`

### Reference Data

#### `GET v1/companies`
All 5,387+ companies registered in the Codal system.

**⚠️ IMPORTANT: Most entries are NOT stocks.** The list includes:
- Regional water authorities, auditors, non-trading entities
- Funds (صندوق), bonds (اوراق بهادار), and other non-equity instruments
- Companies registered with SEO but never listed on an exchange

**To find actual publicly traded stocks**, combine two filters:
1. `st=0` (TSE Bourse) or `st=1` (Fara Bourse) — limits to exchange-listed entities
2. Symbol length ≤ 8 Persian characters — filters out non-trading entities (water authorities, auditors, etc. have long names as symbols)

**Counts from the real data:**
| Group | Count |
|-------|-------|
| Total CODAL entries | 5,388 |
| st=0 (Bourse TSE) | 543 |
| st=1 (Fara Bourse) | 401 |
| st=0 with short symbol (≤8 chars) | 519 |
| Actual active stocks on TSETMC (cross-ref) | ~333 |

**Response**: `list[Company]`
```json
[
  {"sy": "فولاد", "n": "فولاد مبارکه اصفهان", "i": "271018", "t": -1, "st": 0, "IG": 27, "RT": 1000000}
]
```
Fields:
- `sy` — Symbol (نماد)
- `n` — Company name (نام شرکت)
- `i` — ISIC code (کد صنعت)
- `t` — Type (نوع)
- `st` — Company state (وضعیت)
- `IG` — Industry group ID (گروه صنعت)
- `RT` — Reporting type (نوع گزارشگری)

#### `GET v1/categories`
12 categories containing PublisherTypes (6 types) each with LetterTypes.

**Response**: `list[Category]`

Categories:
| Code | Name (Persian) |
|------|----------------|
| -1 | همه موارد |
| 1 | اطلاعات و صورت مالی سالانه |
| 2 | افشااطلاعات با اهمیت و شفاف سازی |
| 3 | گزارش عملکرد ماهانه |
| 4 | اساسنامه / امیدنامه |
| 5 | اطلاعات هئیت مدیره و کمیته حسابرسی |
| 6 | آگهی دعوت به مجامع و تصمیمات |
| 7 | افزایش سرمایه |
| 8 | شفاف سازی مربوط به بورس/فرابورس |
| 9 | شفاف سازی مربوط به سازمان |
| 10 | سایر |
| 11 | اوراق بدهی |

Publisher Types:
| Code | Name |
|------|------|
| 1 | ناشران (Issuers) |
| 2 | کارگزاران (Brokers) |
| 3 | نهاد مالی (Financial Institutions) |
| 4 | نهاد عمومی (Public Institutions) |
| 5 | شرکت دولتي (State-owned Companies) |
| 17 | شرکتهای بخش عمومی و سایر (Public Sector & Other) |

#### `GET v1/IndustryGroup`
72 industry groups.

**Response**: `list[{Id: int, Name: str}]`

#### `GET v1/auditors`
197 auditor firms.

**Response**: `list[{n: str (name), c: str (code)}]`

#### `GET v1/financialYears?Symbol={symbol}`
Fiscal year-end dates for a company.

**Response**: `list[str]` — Jalali dates (e.g., `["1405/12/29", "1404/12/29", ...]`)

### Search

#### `GET v2/q?{params}`
Search for letters/filings with full filter capability.

**Response**: `{Total: int, Page: int, Letters: list[Letter], IsAttacker: bool}`

**Search Parameters** (all optional):

| Param | Type | Description |
|-------|------|-------------|
| `Symbol` | string | Company symbol (e.g., `فولاد`) |
| `Subject` | string | Text search in subject |
| `TracingNo` | int | Specific tracing number (-1 = all) |
| `LetterCode` | string | Letter code filter |
| `LetterType` | string | Letter type ID ("-1" = all) |
| `FromDate` | string | Start date (Jalali `YYYY/MM/DD`) |
| `ToDate` | string | End date (Jalali `YYYY/MM/DD`) |
| `Isic` | string | ISIC code |
| `AuditorRef` | string | Auditor reference ("-1" = all) |
| `YearEndToDate` | string | Fiscal year end date |
| `PageNumber` | int | Page number (default: 1) |
| `Length` | int | Financial period length in months (valid: 1-12, or -1 for all). **NOT** the number of results per page. The default page size is 20. |
| `Audited` | bool | Include audited reports |
| `NotAudited` | bool | Include unaudited reports |
| `IsNotAudited` | bool | Is not audited |
| `Childs` | bool | Include subsidiary companies |
| `Mains` | bool | Include parent companies |
| `Publisher` | bool | Publisher flag |
| `CompanyState` | string | Company state ("-1" = all) |
| `ReportingType` | string | Reporting type ("-1" = all) |
| `name` | string | Company name search |
| `Category` | string | Category ID ("-1" = all) |
| `CompanyType` | string | Company type ("-1" = all) |
| `Consolidatable` | bool | Include consolidatable |
| `NotConsolidatable` | bool | Include not consolidatable |
| `IndustryGroup` | int | Industry group ID |
| `search` | bool | Trigger search flag |

**Letter Response Schema**:
```json
{
  "TracingNo": 1563609,
  "Symbol": "فولاد",
  "CompanyName": "فولاد مبارکه اصفهان",
  "UnderSupervision": 0,
  "Title": "صورت‌های مالی سال مالی منتهی به ۱۴۰۴/۱۲/۲۹ (حسابرسی شده)",
  "LetterCode": "ن-۱۰",
  "SentDateTime": "۱۴۰۵/۰۴/۲۲ ۱۲:۲۶:۳۱",
  "PublishDateTime": "۱۴۰۵/۰۴/۲۲ ۱۲:۲۶:۳۱",
  "HasHtml": true,
  "HasExcel": true,
  "HasPdf": true,
  "HasXbrl": false,
  "HasAttachment": true,
  "IsEstimate": false,
  "Url": "/Reports/Decision.aspx?LetterSerial=...",
  "PdfUrl": "DownloadFile.aspx?hs=...&ft=1005&let=6",
  "ExcelUrl": "https://excel.codal.ir/service/Excel/GetAll/.../0",
  "XbrlUrl": "",
  "AttachmentUrl": "/Reports/Attachment.aspx?LetterSerial=...",
  "TedanUrl": "http://www.tedan.ir",
  "SuperVision": {
    "UnderSupervision": 3,
    "AdditionalInfo": "",
    "Reasons": ["بررسی وضعیت شفافیت اطلاعاتی ناشر"]
  }
}
```

### Report Detail Page

The report page (`/Reports/Decision.aspx`) provides the full HTML rendering of the filing, including financial statements, auditor reports, and signer information.

**URL**: `https://www.codal.ir/Reports/Decision.aspx?LetterSerial={serial}&rt=0&let={letterType}&ct=0&ft=-1`

Key information extracted from the page:
- Company name, symbol, registered capital, ISIC code
- Report period (12-month, 6-month, etc.)
- Audit status (حسابرسی شده / حسابرسی نشده)
- Financial statement tables (balance sheet, income statement, cash flow, etc.)
- Auditor opinion and report
- Signer information (name, membership number, position, signature time)

### File Downloads

| File Type | URL Pattern |
|-----------|-------------|
| **PDF** | `https://www.codal.ir/DownloadFile.aspx?hs={serial}&ft=1005&let={letterType}` |
| **Excel** | `https://excel.codal.ir/service/Excel/GetAll/{serial}/0` |
| **Attachment** | `https://www.codal.ir/Reports/Attachment.aspx?LetterSerial={serial}` |

**⚠️ Serial-to-URL dependency:** To construct any download URL, you MUST first have the `{serial}` (LetterSerial). The serial is ONLY available through the CODAL search API (v2/q) — it is NOT derivable from ticker+fiscal-year alone. If the search API is down/429, you cannot generate download links.

**⚠️ Pipeline serial persistence gap:** The pipeline script downloads Excel files via serial but does NOT save the serial in its JSON output. Raw/excel files are saved with filenames like `{ticker}_{year}_{month}_{day}.html`, which contain no serial info. Download URLs CANNOT be reconstructed from pipeline output alone — the serial must be saved explicitly if link reconstruction is needed later.

**User-facing convention:** When asked for "download links", provide actual clickable `https://excel.codal.ir/service/Excel/GetAll/{serial}/0` URLs — NOT ticker+date metadata lists. If serials are unavailable (API down, no persistence in output), state this clearly, show the URL pattern, and explain why you cannot produce live links. The fallback is CODAL web search URLs (`https://codal.ir/ReportList.aspx?Symbol={ticker}`), but note that `www.codal.ir` has been returning server errors since July 2026.

### Rate Limiting (Updated July 2026)

The search API (`search.codal.ir/api/search/`) has aggressive DDoS protection that returns **429 Too Many Requests** after ~35-45 requests at 1s intervals.

**Key facts (updated July 2026):**
- **429 is extremely persistent** — observed to persist for **hours** (10+ minutes, 30+ minutes, potentially hours), not the 3 minutes reported in earlier documentation. Exponential backoff starting at 1min is recommended, with a maximum wait of 600s+ before giving up on a retry.
- **Entire search.codal.ir subdomain is blocked** — once rate-limited, ALL endpoints on that subdomain (search v1/v2, financialYears, companies, etc.) return 429 simultaneously. The main site `www.codal.ir` also returns "unknown error" on all subpages (Search.aspx, ReportList.aspx, Decision.aspx) — this may be a separate server-side issue.
- **Captcha endpoint returns 404** — `POST /api/ddos/v1/begin` at `www.codal.ir` now returns HTTP 404. The automated captcha bypass path has been removed. Do not rely on it.
- **Excel service bypasses rate limit** — `excel.codal.ir/` is a separate domain and continues to work even while `search.codal.ir` is blocked. Use this to download known filings during cooldown.
- **curl_cffi workaround** — Using `curl_cffi` with `impersonate="chrome120"` and proper session cookie management (`requests.Session`) can sometimes bypass the rate limit. The `TS018fb0f7` cookie from Traffic Server appears to be the session key. However, this workaround is unreliable — it may work for a few requests then re-trigger 429.

**Recommended strategy (large-scale pipelines):**\n- Use `YearEndToDate` filter to find each fiscal year in ONE search call (avoid pagination through dozens of pages)\n- Use `curl_cffi` with `impersonate=\"chrome120\"` and a persistent `requests.Session` for better browser fingerprint mimicry — this sometimes bypasses the 429 when raw urllib fails\n- Max **20-25 requests** per session before a 3-minute cooldown\n- On 429: exponential backoff (1min → 2min → 4min → 8min → 16min — give up after 5 retries)
- **3s delay** between requests minimum
- Separate search phase from download phase — Excel downloads happen on a different domain and are NOT rate-limited
- For large-scale pipelines: run as a persistent background process (screen/cron) that makes slow progress over hours
- **Alternative: TSETMC Codal proxy** — `cdn.tsetmc.com/api/Codal/GetPreparedDataByInsCode/{n}/{insCode}` returns report metadata (tracingNo, dates, hasExcelReport flags) **with no rate limiting** and from anywhere in the world. Use this for discovery, then resolve serials via CODAL search in a separate phase.

**Expected throughput for a 409-stock × 15-year pipeline:**
- ~6,000 search requests at 3s delay = ~5 hours of request time
- ~240 rate limit resets × 3min cooldown = ~12 hours overhead
- Total (single server): ~24-35 hours.
- **With 5 parallel servers** (different source IPs, disjoint stock ranges): **~6-8 hours** observed.

**Parallel server scaling** — CODAL rate-limits by source IP (not by account). N identical pipelines from N different IPs give roughly N× throughput. Zero coordination needed — each server independently gets its own rate-limit bucket.

### Per-IP rate limiting variance (July 2026 finding)

Different source IPs experience **different rate-limit strictness** from CODAL, even when all are inside Iran. During a 5-server parallel run, Server A (a specific Iranian IP) triggered 429 after every ~20 requests at 2.5s delay, while other servers (from a different IP range) running identical code showed no such throttling.

**Root cause**: CODAL applies IP-specific rate-limit tiers. Some IP ranges have tighter sliding windows than others — probably based on historical traffic patterns to those IPs.

**Detection**: A server that shows repeated `⏳ Cooldown 180s...` messages with little actual progress (1-2 stocks per 30 min vs. 5-10 on other servers) is likely on a stricter IP.

**Fix**: Switch to **continuous mode** — disable the artificial batch cooldown and rely on a longer per-request delay to stay under the threshold:

| Setting | Default | Continuous (stricter IP) | Effect |
|---------|---------|------------------------|--------|
| `DELAY` | 2.5s | **5.0s** | Lowers request rate below sliding-window threshold |
| `BATCH_MAX` | 20 | **999** | No artificial cooldown — continuous stream |
| `COOLDOWN` | 180s | 300s | Fallback only (rarely fires with BATCH_MAX=999) |
| Max FYs/stock | 15 | **10** | 21 requests/stock instead of 31 (fewer trips past limit) |

After switching to continuous mode on Server A, the pipeline ran at **~3 stocks per 5 minutes** with **zero 429 retries**, vs. 6 stocks in 30+ minutes with repeated batch cooldowns. The key insight: with a long enough delay (5s), you never hit the rate limit at all, so batch cooldowns become pure wasted time.

**When to use**: Always try the default batch-cooldown settings first on a new server. If it shows repeated cooldown cycles, patch that server's config to continuous mode. Other servers can keep the default settings.

### API Response Format: Content Negotiation (JSON vs XML)

The CODAL API at `search.codal.ir` supports **content negotiation** via the `Accept` header. Different Accept headers yield different response formats:

| Accept Header | Response Format | v1/financialYears | v2/q |
|---------------|-----------------|-------------------|------|
| `Accept: application/json` | **JSON** ✅ | `["1405/12/29", "1404/12/29"]` | JSON object with `{Total, Page, Letters}` |
| `Accept: text/html,...` (default) | **XML** | `<ArrayOfstring>` | `<SearchReportListDto>` with `<CodalLetterHeaderDto>` |

**Always set `Accept: application/json`** in your request headers. Without it, `json.loads()` fails and it looks like the API is broken.

```python
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
```

If you must parse the XML fallback:
- `financialYears`: `<ArrayOfstring xmlns="http://schemas.microsoft.com/2003/10/Serialization/Arrays">` — parse with `xml.etree.ElementTree`
- `v2/q`: `<SearchReportListDto>` with `<CodalLetterHeaderDto>` items — extract with regex
- Legacy endpoints (`v1/companies`, `v1/categories`, `v1/IndustryGroup`, `v1/auditors`) return JSON regardless of Accept header.

**⚠️ Pitfall:** Using `urllib.request` defaults (no Accept) returns XML. `json.loads()` fails with "unexpected character at line 1 column 1" — which looks like the API is broken. Always set `Accept: application/json`.

## Letter Types (ناشران / Issuers)

Key letter types for Category 1 (اطلاعات و صورت مالی سالانه):

| ID | Name (Persian) |
|----|----------------|
| 6 | اطلاعات و صورتهای مالی میاندوره ای |
| 30 | زمانبندی پرداخت سود |
| 32 | گزارش فعالیت هیئت مدیره |
| 90 | گزارش کنترل های داخلی |
| 180 | اظهارنامه مالیاتی |
| 181 | عدم فعالیت شرکت با اعلام به حوزه مالیاتی |
| 2225 | زمانبندی پرداخت سود سنوات گذشته |

Key letter types for Category 2 (افشااطلاعات با اهمیت):

| ID | Name (Persian) |
|----|----------------|
| 1 | اولین پیش بینی درآمد هر سهم |
| 2 | پیش بینی درآمد هر سهم |
| 11 | افشای اطلاعات با اهمیت |
| 128 | شفاف سازی در خصوص شایعه، خبر یا گزارش منتشر شده |
| 147 | شفاف سازی در خصوص نوسان قیمت سهام |
| 148 | اطلاعات حاصل از برگزاری کنفرانس اطلاع رسانی |

Key letter types for Category 3 (گزارش عملکرد ماهانه):

| ID | Name (Persian) |
|----|----------------|
| 8 | صورت وضعیت پورتفوی |
| 58 | گزارش فعالیت ماهانه |

Key letter types for Category 6 (آگهی دعوت به مجامع):

| ID | Name (Persian) |
|----|----------------|
| 16 | آگهی دعوت به مجمع عمومی عادی سالیانه |
| 17 | آگهی دعوت به مجمع عمومی عادی بطور فوق العاده |
| 18 | آگهی دعوت به مجمع عمومی فوق العاده |
| 20 | تصمیمات مجمع عمومی عادی سالیانه |
| 22 | تصمیمات مجمع عمومی فوق‌العاده |
| 2020 | خلاصه تصمیمات مجمع عمومی عادی سالیانه |

Key letter types for Category 7 (افزایش سرمایه):

| ID | Name (Persian) |
|----|----------------|
| 23 | زمان تشکیل جلسه هیئت‌مدیره در خصوص افزایش سرمایه |
| 24 | تصمیمات هیئت‌مدیره در خصوص افزایش سرمایه |
| 25 | مهلت استفاده از حق تقدم خرید سهام |
| 27 | اعلامیه پذیره نویسی عمومی |
| 28 | آگهی ثبت افزایش سرمایه |
| 55 | پیشنهاد هیئت مدیره به مجمع عمومی فوق العاده در خصوص افزایش سرمایه |

See `references/letter-types.md` for the complete list of all ~100+ letter types across all categories.

## Workflows

### Workflow 1: Search for Letters by Symbol (XML Parsing)

**IMPORTANT**: The CODAL API returns **XML** (Content-Type: application/xml), not JSON. Using `json.loads()` on the response will fail with "unexpected character at line 1 column 1". Use regex to extract `<CodalLetterHeaderDto>` elements instead.

```python
import urllib.request, urllib.parse, re

def search_codal(symbol: str, page: int = 1) -> list[dict]:
    """Search for filings by company symbol. Parses XML response."""
    url = "https://search.codal.ir/api/search/v2/q?Symbol=" + urllib.parse.quote(symbol) + "&PageNumber=" + str(page)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    xml_text = resp.read().decode("utf-8")
    
    # Parse XML — letter elements use <CodalLetterHeaderDto> tags (NOT <Letter>)
    letters = re.findall(r"<CodalLetterHeaderDto[^>]*>(.*?)</CodalLetterHeaderDto>", xml_text, re.DOTALL)
    result = []
    for letter in letters:
        def get(tag):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", letter, re.DOTALL)
            return m.group(1) if m else ""
        result.append({
            "TracingNo": get("TracingNo"),
            "Symbol": get("Symbol"),
            "Title": get("Title"),
            "HasExcel": get("HasExcel") == "true",
            "Url": get("Url"),
            "ExcelUrl": get("ExcelUrl"),
            "SentDateTime": get("SentDateTime"),
        })
    return result

# Find all filings for فولاد
results = search_codal("فولاد")
print(f"Found {len(results)} letters")
for letter in results[:5]:
    print(f"  [{letter['TracingNo']}] {letter['Title'][:60]}")
    print(f"    Excel: {letter['ExcelUrl'][:60]}")
```

### Workflow 1b: Search by TracingNo (Single-Result, Fast)

When you already have the TracingNo (e.g., from TSETMC Codal proxy `GetPreparedDataByInsCode`), search directly by TracingNo to get the LetterSerial in one call. No pagination needed.

```python
def search_by_tracing_no(tracing_no: int) -> dict | None:
    \"\"\"Find a specific filing by its TracingNo. Returns the serial and title.\"\"\"
    url = f\"https://search.codal.ir/api/search/v2/q?TracingNo={tracing_no}\"
    req = urllib.request.Request(url, headers={\"User-Agent\": \"Mozilla/5.0\"})
    resp = urllib.request.urlopen(req)
    xml_text = resp.read().decode(\"utf-8\")
    
    letters = re.findall(r\"<CodalLetterHeaderDto[^>]*>(.*?)</CodalLetterHeaderDto>\", xml_text, re.DOTALL)
    if not letters:
        return None
    letter = letters[0]
    serial = \"\"
    url_match = re.search(r\"<Url[^>]*>(.*?)</Url>\", letter)
    if url_match and \"LetterSerial=\" in url_match.group(1):
        serial = url_match.group(1).split(\"LetterSerial=\")[1].split(\"&\")[0]
    if not serial:
        eu = re.search(r\"<ExcelUrl[^>]*>(.*?)</ExcelUrl>\", letter)
        if eu and eu.group(1) and \"/GetAll/\" in eu.group(1):
            serial = eu.group(1).split(\"/GetAll/\")[1].split(\"/\")[0]
    title_m = re.search(r\"<Title>(.*?)</Title>\", letter)
    return {\"serial\": serial, \"title\": title_m.group(1) if title_m else \"\"}
```

### Workflow 2: Get Company Reference Data

```python
def get_companies() -> list[dict]:
    """Get all companies registered in Codal."""
    url = "https://search.codal.ir/api/search/v1/companies"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def get_industry_groups() -> list[dict]:
    """Get all industry groups."""
    url = "https://search.codal.ir/api/search/v1/IndustryGroup"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def get_letter_categories() -> list[dict]:
    """Get all letter categories with their publisher types and letter types."""
    url = "https://search.codal.ir/api/search/v1/categories"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())
```

### Workflow 3: Filter by Letter Type

```python
def search_by_letter_type(symbol: str, letter_type: int, **extra) -> dict:
    """Search for specific letter types for a company.
    Common letter types: 6=Interim Financial, 58=Monthly Report, 11=Important Disclosure, 16=Shareholder Meeting Notice
    NOTE: Do NOT pass Length — it is a period-length filter (1-12 months), not a page size.
    """
    import urllib.parse
    params = {
        "Symbol": symbol,
        "LetterType": str(letter_type),
        "PageNumber": "1",
    }
    params.update(extra)
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = "https://search.codal.ir/api/search/v2/q?" + query
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())
```
# Example: Get monthly reports for فولاد
monthly = search_by_letter_type("فولاد", 58)
for letter in monthly['Letters']:
    print(f"{letter['YearEndToDate']}: {letter['Title'][:80]}")
```

### Workflow 4: Get Financial Years (XML Parsing)

```python
import urllib.request, urllib.parse, xml.etree.ElementTree as ET

def get_financial_years(symbol: str) -> list[str]:
    """Get fiscal year-end dates. Returns XML ArrayOfstring — parse with ElementTree."""
    url = f"https://search.codal.ir/api/search/v1/financialYears?Symbol={urllib.parse.quote(symbol)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    root = ET.fromstring(resp.read())
    ns = {"ns": "http://schemas.microsoft.com/2003/10/Serialization/Arrays"}
    return [e.text for e in root.findall("ns:string", ns) if e.text]

# Get fiscal years for فولاد
years = get_financial_years("فولاد")
print(years)  # ['1405/12/29', '1404/12/29', '1403/12/30', ...]
```

### Workflow 5: Download Report Files

```python
def get_report_url(serial: str, letter_type: int) -> dict:
    """Get URLs for the report page, PDF, and Excel."""
    import urllib.parse
    encoded = urllib.parse.quote(serial)
    return {
        "html": f"https://www.codal.ir/Reports/Decision.aspx?LetterSerial={encoded}&rt=0&let={letter_type}&ct=0&ft=-1",
        "pdf": f"https://www.codal.ir/DownloadFile.aspx?hs={encoded}&ft=1005&let={letter_type}",
        "excel": f"https://excel.codal.ir/service/Excel/GetAll/{encoded}/0",
        "attachment": f"https://www.codal.ir/Reports/Attachment.aspx?LetterSerial={encoded}",
    }

# Get the LetterSerial from a search result
# serial = results['Letters'][0]['Url'].split('LetterSerial=')[1].split('&')[0]
# urls = get_report_url(serial, 6)
```

### Workflow 6: Search by Date Range

```python
def search_by_date_range(symbol: str, from_date: str, to_date: str, **extra) -> dict:
    \"\"\"Search filings within a date range. Dates are Jalali (e.g., '1405/01/01').\"\"\"
    import urllib.parse
    params = {\"Symbol\": symbol, \"FromDate\": from_date, \"ToDate\": to_date, \"PageNumber\": \"1\"}
    params.update(extra)
    query = \"&\".join(f\"{k}={urllib.parse.quote(str(v))}\" for k, v in params.items())
    url = \"https://search.codal.ir/api/search/v2/q?\" + query
    req = urllib.request.Request(url, headers={\"User-Agent\": \"Mozilla/5.0\"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())
```

### Workflow 7: Find All Actually Traded Stocks (Cross-Reference with TSETMC)

The `v1/companies` endpoint is the best starting point for building a stock universe, but requires filtering AND cross-referencing with TSETMC because:

1. Many st=0 (TSE-listed) entities are actually **funds** (صندوق) or **tranche instruments** (بخشی), not common stocks
2. TSETMC `MarketWatchInit` is also incomplete — some major stocks (like فولاد) are missing from it
3. A dual-source merge (CODAL + TSETMC) yields the most complete universe

**Match rate reality:** Only ~60-65% of CODAL TSE stocks (st=0, short symbol) will match an active TSETMC common stock (yVal=300, flow=1). The rest are funds misclassified as st=0, delisted stocks, or non-trading entities.

**Complete pipeline:** See `references/building-stock-universe.md` in the **tsetmc** skill for the full end-to-end process (batch search, dedup normalization, sector fetch, quality audit). That reference covers the full pipeline from both data sources.

```python
def get_traded_stocks() -> list[dict]:
    \"\"\"Get all exchange-listed stocks from Codal, filtering out non-stock entities.\"\"\"
    import urllib.request, json
    
    url = \"https://search.codal.ir/api/search/v1/companies\"
    req = urllib.request.Request(url, headers={\"User-Agent\": \"Mozilla/5.0\"})
    resp = urllib.request.urlopen(req)
    companies = json.loads(resp.read())
    
    stocks = []
    for c in companies:
        st = c.get(\"st\", -1)
        sy = c.get(\"sy\", \"\").strip()
        # Keep only exchange-listed (st=0 TSE, st=1 Fara Bourse) with short ticker symbols
        if st in (0, 1) and len(sy) <= 8:
            stocks.append(c)
    
    return stocks

# Then cross-reference with TSETMC:
# 1. Batch-search each CODAL symbol on TSETMC CDN search API (cdn.tsetmc.com, works globally)
# 2. Merge with MarketWatchInit yVal=300, flow=1 instruments
# 3. Deduplicate by normalized ticker (strip \"3\"/\"2\" suffixes, normalize Yeh)
# 4. Fetch sector info, filter out fund sectors
# See tsetmc skill -> references/building-stock-universe.md for complete code
```

### Workflow 8: Extract Financial Statements for FF Factors

This workflow finds parent-company annual reports and extracts Book Equity, Revenue, COGS, SG&A, Interest, and Net Income for factor construction.

**Key insight: Use `YearEndToDate` to find each fiscal year in a single search call** — avoids pagination through dozens of pages of subsidiary reports.

```python
import urllib.request, urllib.parse, json, re, time, xml.etree.ElementTree as ET

# 1. Get fiscal years (XML parsing)
def get_fiscal_years(symbol: str) -> list[str]:
    url = f"https://search.codal.ir/api/search/v1/financialYears?Symbol={urllib.parse.quote(symbol)}"
    resp = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
    root = ET.fromstring(resp.read())
    ns = {"ns": "http://schemas.microsoft.com/2003/10/Serialization/Arrays"}
    return [e.text for e in root.findall("ns:string", ns) if e.text]

# 2. Find parent-company annual report for ONE fiscal year (XML parsing)
def find_annual_report(symbol: str, fy: str) -> dict | None:
    params = {"Symbol": symbol, "Category": "1", "Length": "12", "YearEndToDate": fy, "PageNumber": "1"}
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"https://search.codal.ir/api/search/v2/q?{query}"
    resp = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
    xml_text = resp.read().decode("utf-8")
    
    # Parse CodalLetterHeaderDto elements from XML
    letters = re.findall(r"<CodalLetterHeaderDto[^>]*>(.*?)</CodalLetterHeaderDto>", xml_text, re.DOTALL)
    for letter in letters:
        title_m = re.search(r"<Title[^>]*>(.*?)</Title>", letter)
        url_m = re.search(r"<Url[^>]*>(.*?)</Url>", letter)
        excel_m = re.search(r"<HasExcel[^>]*>(.*?)</HasExcel>", letter)
        if not title_m: continue
        title = title_m.group(1)
        tn = title.replace("\u064a", "\u06cc").replace("\u0643", "\u06a9")
        if "صورت" not in tn or "مالی" not in tn or "سال مالی" not in tn: continue
        if "(شرکت" in tn: continue  # skip subsidiaries
        serial = ""
        if url_m and "LetterSerial=" in url_m.group(1):
            serial = url_m.group(1).split("LetterSerial=")[1].split("&")[0]
        if serial and excel_m and excel_m.group(1) == "true":
            return {"fy": fy, "serial": serial, "audited": "حسابرسی شده" in title}
    data = json.loads(resp.read())
    
    for letter in data.get("Letters", []):
        title = letter.get("Title", "")
        tn = title.replace("\\u064a", "\\u06cc").replace("\\u0643", "\\u06a9")  # normalize
        # Parent report: has "صورت" + "مالی" + "سال مالی" AND NO "(شرکت" (subsidiary)
        if "صورت" not in tn or "مالی" not in tn or "سال مالی" not in tn: continue
        if "(شرکت" in tn: continue  # skip subsidiary reports
        serial = ""
        if "LetterSerial=" in letter.get("Url", ""):
            serial = letter["Url"].split("LetterSerial=")[1].split("&")[0]
        if serial and letter.get("HasExcel"):
            return {"fy": fy, "serial": serial, "audited": "حسابرسی شده" in title}
    return None

# 3. Download Excel HTML and parse
def download_excel_html(serial: str) -> str:
    url = f"https://excel.codal.ir/service/Excel/GetAll/{serial}/0"
    resp = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30)
    return resp.read().decode("utf-8")

# Full pipeline for one stock
def get_all_financials(symbol: str) -> dict:
    \"\"\"Get financial statements for all available years for a symbol.\"\"\"
    fys = get_fiscal_years(symbol)
    recent = [fy for fy in fys if int(fy[:4]) >= 1388][-15:]  # last ~15 years
    
    results = {}
    for fy in recent:
        time.sleep(2)  # rate limit safety
        report = find_annual_report(symbol, fy)
        if not report: continue
        
        time.sleep(1)  # rate limit safety
        html = download_excel_html(report["serial"])
        parsed = parse_financials(html)  # see references/post-pipeline-quality-check.md § How to Fix Parser Coverage for the v3 approach (Persian normalization, exclusion rules, multi-table selection)
        if parsed:
            parsed["audited"] = report["audited"]
            results[fy] = parsed
    
    return results
```

**Expected output structure:**
```json
{
  "total_assets": 540734681.0,
  "total_equity": 339197399.0,
  "revenue": 300940815.0,
  "cogs": 166741080.0,
  "sga": 11344709.0,
  "interest": 12282236.0,
  "op_profit": 150092791.0,
  "net_income": 166026012.0
}
```

See `references/excel-html-format.md` for detailed table structure and parsing code.

### Workflow 9: Large-Scale Extraction Pipeline on Remote Server

For projects needing financial data from hundreds of stocks across many years (e.g., factor construction), run a persistent pipeline on a server in Iran that respects rate limits and provides progress feedback.

#### Architecture

Single server:
```
LOCAL MACHINE                           PRIMARY SERVER (Iran)
┌────────────────────┐                  ┌─────────────────────────┐
│ progress monitor   │  ─── SSH ───→    │ screen session          │
│ (cron every 15 min)│                  │   ├── loop over stocks  │
│ → SSH check        │                  │   ├── 180s cooldown     │
│ → compute ETA      │                  │   ├── save JSON+HTML    │
│ → deliver (Telegram)│                 │   └── stdout→screenlog  │
└────────────────────┘                  └─────────────────────────┘
```

Parallel multi-server (throughput scales with server count since CODAL rate-limits by IP):
```
LOCAL MACHINE
    ├── SSH → SERVER A (screen) — stocks[0:N1]
    ├── SSH → SERVER B (screen) — stocks[N1:N2]
    └── SSH → SERVER C (screen) — stocks[N2:409]
                 all same script, same universe, different start_idx+limit
```
All servers run the identical pipeline script; the `start_idx` and `limit` arguments divide the work. No shared state needed. Each server gets its own IP and its own rate limit bucket. Monitoring queries all and reports combined progress.

**Quick server discovery** — Before committing a new server, check its country and CODAL access in one SSH call:
```bash
ssh your-server 'curl -s https://ifconfig.co/country-iso 2>/dev/null; echo; \
  curl -s -o /dev/null -w "%{http_code}" \
    "https://search.codal.ir/api/search/v2/q?Symbol=%D8%A2%D8%A8%D8%A7%D8%AF%D8%A7&Category=1" --max-time 10'
```
`IR` + `200` = inside Iran, CODAL works. `AZ` + `200` = outside Iran but CODAL works (observed from Azerbaijan). Any other HTTP code means the server cannot reach CODAL.

**Fleet server setup pattern** — When setting up multiple VPSs to parallelize, follow this general pattern per server:

1. **Test direct SSH** — Verify basic connectivity before investing time in setup:
   ```bash
   ssh your-server 'whoami'
   ```
2. **Set up shared SSH key** — Use the same SSH key for all servers. Copy via SSH:
   ```bash
   ssh-copy-id -o StrictHostKeyChecking=accept-new your-server
   ```
3. **If direct SSH fails** (some servers block inbound), copy the public key through an intermediary server that can reach both:
   ```bash
   cat ~/.ssh/your-key.pub | ssh your-iran-server \
     "ssh your-server 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'"
   ```
   Then connect via a jump host if needed.
4. **Install deps** — `sudo apt-get install -y python3-venv screen && python3 -m venv ~/venv && ~/venv/bin/pip install curl_cffi`
5. **Transfer files** — your stock universe file and the pipeline script
6. **Start in screen** — `screen -dmSL pipeline-session ~/venv/bin/python3 your-extraction-script <limit> <start_idx>`
7. **Add to monitoring** — Build the SSH command for this server (direct or via jump host), add to the monitoring script.

Same-IP-range, different-country reality: Provider IP ranges may span multiple countries. Always test before committing setup time.

**3+ server setup** — When the same IP range yields servers in different countries (Iran + Azerbaijan), test each. Some may need a jump host through the primary server if they block inbound SSH from outside. Split the universe into disjoint ranges (e.g., 0-99, 100-199, 200-408) and start each with its range.

See `references/large-scale-pipeline-example.md` for the full setup flow (password-to-key, deps, screen, monitoring).

#### Key Elements

1. **Deploy via pipe** — Write the script locally (full editing), then pipe to remote for execution:
   ```bash
   cat pipeline.py | ssh your-server 'cat > /tmp/pipeline.py && python3 /tmp/pipeline.py'
   ```

2. **Persist with screen** — Run inside a detached screen session so it survives SSH disconnects:
   ```bash
   ssh your-server 'screen -dmSL pipeline-session python3 /tmp/pipeline.py'
   ```
   Screen captures stdout to `~/screenlog.0` — readable via subsequent SSH calls.

3. **Skip already-done stocks** — Check for existing output files before processing:
   ```python
   if os.path.exists(f"/tmp/results/{symbol}.json"):
       print(f"⏭️ {symbol} (already done)")
       continue
   ```

4. **Cache raw source data** — Save raw HTML alongside parsed JSON. This lets you re-parse with improved extraction code without re-downloading (and re-triggering rate limits).

5. **Cache raw source data** — Save raw HTML alongside parsed JSON. This lets you re-parse with improved extraction code without re-downloading (and re-triggering rate limits). The pipeline script saves every downloaded Excel HTML to `output_dir/raw/{symbol}_{fy}.html`. At ~200-500KB per file, 409 stocks × 15 years ≈ 1.2GB total — well within a cheap VPS's disk budget and invaluable for post-pipeline re-parsing.

6. **Monitor via cron + SSH across all servers** — For multi-server fleets, deploy a status script to each server that outputs pipe-delimited status, then query all from a central monitoring script. Each server's SSH command is built independently — some need a jump host, some are direct:

   ```python
   import subprocess
   
   def get(ssh_cmd):
       r = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=20)
       parts = r.stdout.strip().split("|")
       return {"stocks": int(parts[0]), "fy": int(parts[1]),
               "html": int(parts[2]), "run": parts[3], "cur": parts[4]}
   
   # Each server has its own SSH command
   st = [
       ("Primary (Iran)",  get(["ssh", "your-iran-server", "python3 /tmp/status_check.py"])),
       ("Server B",        get(["ssh", "-oProxyJump=your-iran-server", "your-server-b", "python3 /tmp/status_check.py"])),
       ("Server C",        get(["ssh", "-oProxyJump=your-iran-server", "your-server-c", "python3 /tmp/status_check.py"])),
   ]
   
   total_done = sum(s["stocks"] for _, s in st)
   ```

   The status check script (deployed to each server) outputs a single pipe-delimited line:
   ```
   stocks_done|fy_records|html_files|running_flag|current_stock
   ```

   Schedule via `hermes cron create --schedule 15m` with the reporting script. Include `rsync -az --delete` from the primary server to a local directory as a data backup — server VPSs are ephemeral (one was accidentally deleted mid-session and all its work was lost).

7. **ETA calculation** — Estimate remaining time based on done/total and per-stock cooldown:
   ```python
   remaining = TOTAL - done
   eta_seconds = remaining * SECONDS_PER_STOCK
   # Format: ~Xh Ym or ~Xd Xh depending on magnitude
   ```

8. **Progress bar** — A simple character-based bar keeps the report scannable at a glance:
   ```python
   pct = (done / TOTAL) * 100
   filled = int(20 * pct / 100)
   bar = "\u2588" * filled + "\u2591" * (20 - filled)
   ```

9. **Per-server config tuning for aggressive IPs** — Different CODAL rate-limit tiers affect server throughput. When a server shows repeated cooldowns with minimal progress (1-2 stocks per 30 min while others do 5-10), patch its config on that specific server to continuous mode:

   | Setting | Default | Continuous (stricter IP) |
   |---------|---------|--------------------------|
   | `DELAY` | 2.5s | 5.0s |
   | `BATCH_MAX` | 20 | 999 |
   | `COOLDOWN` | 180s | 300s (unused) |
   | `recent` FYs | `[-15:]` | `[-10:]` |

   The key: with a long enough delay, CODAL never rate-limits you, so batch cooldowns are wasted time. Edit the config on the remote server via Python in-place replacement:

   ```bash
   ssh your-server 'python3 -c "
   p = \"/tmp/your-extraction-script\"
   c = open(p).read()
   c = c.replace(\"DELAY = 2.5\", \"DELAY = 5.0\")
   c = c.replace(\"BATCH_MAX = 20\", \"BATCH_MAX = 999\")
   c = c.replace(\"COOLDOWN = 180\", \"COOLDOWN = 300\")
   open(p, \"w\").write(c)
   "'
   ```

   Then kill the screen and restart — the skip-done logic ensures already-processed stocks are not re-fetched.

   #### Speeding up a running pipeline (when not rate-limited)

If you know your server IP is **not** aggressively rate-limited (few or no `⏳ Cooldown` messages), you can accelerate the pipeline by tightening the config on that specific server:

| Setting | Default | Accelerated | Speed gain |
|---------|---------|-------------|------------|
| `DELAY` | 2.5s | **1.5s** | ~1.7× faster requests |
| `BATCH_MAX` | 20 | **30** | Fewer cooldown breaks |
| `COOLDOWN` | 180s | **60s** | 3× faster recovery |

Edit on the remote server, then kill screen and restart (skip-done avoids rework):

```bash
ssh your-server 'python3 -c "
p = \"/tmp/your-extraction-script\"
c = open(p).read()
c = c.replace(\"DELAY = 2.5\", \"DELAY = 1.5\")
c = c.replace(\"BATCH_MAX = 20\", \"BATCH_MAX = 30\")
c = c.replace(\"COOLDOWN = 180\", \"COOLDOWN = 60\")
open(p, \"w\").write(c)
"
screen -S pipeline-session -X quit
screen -dmS pipeline-session bash -c "python3 /tmp/your-extraction-script <limit> <start_idx> 2>&1 | tee /tmp/pipeline.log"'
```

**When to accelerate vs. slow down:**
- If the log shows `✅` completions with few `⏳` messages → accelerate (your IP is lenient)
- If the log shows mostly `⏳ Cooldown 180s...` and barely any `✅` → switch to continuous mode (stricter IP)
- If the pipeline gets `429 Too Many Requests` → you've pushed too far; switch to continuous mode with 5s delay

The key insight: different IPs get different rate-limit tiers from CODAL. Test with conservative settings first, then tune up or down based on observed behavior.

**Pre-flight check**: Before accelerating, verify the server actually processes steadily. Run `tail -20 /tmp/pipeline.log | grep -c '✅'` to get recent completion rate. A rate of ≥3 ✅ per minute is healthy.

#### When to Use This Pattern

- Hundreds of stocks × multiple years of data to fetch
- Rate-limited API (CODAL 429 after ~35-45 requests, persist for hours)
- API is geo-restricted (must run from Iran-based server)
- Pipeline takes hours or days to complete (not minutes)
- User wants periodic Telegram updates while it runs

**Post-pipeline reconciliation**: When the initial multi-server run finishes, some stocks are still missing. See `references/large-scale-pipeline-example.md` § Post-Pipeline Reconciliation for the tail-end workflow: finding exact gaps, re-targeting the fastest server on the missing block, syncing results back, and verifying completeness.

## Archive Completed Data to Google Drive

After the pipeline finishes and raw HTML is organized, the final deliverable is a **compressed archive on Google Drive** for backup and sharing.

### Principle: zip first, upload once

**Never upload thousands of individual files via the Drive API** — a single 93 MB archive replaces 4,652 API calls. The user will correct you if you try the individual route (observed: "we should have zipped it and then send it to google drive").

### Procedure

**1. Clean up the Google Drive folder** (if a previous partial upload exists):
```python
# Find and trash the old folder
r = service.files().list(
    q="name='MyFolder' and mimeType='application/vnd.google-apps.folder' and trashed=false",
    fields='files(id)').execute()
if r.get('files'):
    service.files().update(fileId=r['files'][0]['id'], body={'trashed': True}).execute()
```

**2. Compress the data directory** (from 1.4 GB raw → ~93 MB):
```bash
tar czf /tmp/codal_data.tar.gz -C data codal/
```

**3. Create the Drive folder structure** and upload:
```python
from googleapiclient.http import MediaFileUpload

# Create root folder
root = service.files().create(body={
    'name': 'your-project-name',
    'mimeType': 'application/vnd.google-apps.folder'
}, fields='id').execute()

# Create subfolder
sub = service.files().create(body={
    'name': 'codal',
    'mimeType': 'application/vnd.google-apps.folder',
    'parents': [root['id']]
}, fields='id').execute()

# Upload single compressed archive
media = MediaFileUpload('/tmp/codal_data.tar.gz',
    mimetype='application/gzip', resumable=True)
f = service.files().create(body={
    'name': 'codal_data.tar.gz',
    'parents': [sub['id']]
}, media_body=media, fields='id').execute()
```

**4. Notify the user on Telegram** — after the upload completes (usually in <2 min for a 93 MB file), send the Drive link:
```bash
python3 ~/.hermes/skills/social-media/telegram/scripts/send_message.py \
  "✅ Data uploaded to Google Drive\n\n📁 Folder → codal/codal_data.tar.gz\n🔗 https://drive.google.com/drive/folders/ROOT_ID"
```

### Pitfalls

- **Uploading individual files vs single archive** — The Drive API handles 4,652 individual file uploads at ~0.25s per API call = ~20+ minutes. A single 93 MB archive uploads in <2 minutes. Always compress first.
- **Persian folder names work in Drive** — Google Drive handles Unicode folder names natively. No encoding issues.
- **93 MB is well under Drive's free tier quota** (15 GB) and Telegram's bot API file limit (50 MB). If the archive exceeds 50 MB, split with `split -b 25M` and send via Telegram as multi-part.
- **Expired OAuth token** — The Google token expires ~1 hour after authorization. Before uploading, refresh it: `creds.refresh(Request())`. The script above handles this.
- **Drive folder name collision** — If you trash a folder and create a new one with the same name, both appear in the Drive trash. Drive's API `list` with `trashed=false` correctly returns only the new one.

## Post-Pipeline Data Organization

After the multi-server pipeline finishes and data is synced to the local machine, three housekeeping steps prepare the data for use and archival:

### 1. Organize Raw HTML into Per-Company Directories

Raw HTML files are stored flat by default (e.g., `raw/فملی_1397_12_29.html`). For archiving and human browsing, organize them into per-company directories:

```python
import os, shutil

raw = 'data/codal/raw'
for fname in os.listdir(raw):
    if not fname.endswith('.html'):
        continue
    ticker = fname.split('_')[0]       # ticker is before first underscore
    tdir = os.path.join(raw, ticker)
    os.makedirs(tdir, exist_ok=True)
    shutil.move(os.path.join(raw, fname), os.path.join(tdir, fname))
```

Result:
```
data/codal/raw/
├── فملی/
│   ├── فملی_1397_12_29.html
│   ├── فملی_1398_12_29.html
│   └── ...
├── فولاد/
│   ├── فولاد_1397_12_29.html
│   └── ...
└── (408 company dirs)
```

**Pattern reliability**: Persian tickers never contain underscores in the ticker name, so splitting on `_` and taking `parts[0]` is safe. The rest of the filename is always `YYYY_MM_DD.html`.

### 2. Update `_status.json` After Syncing

After syncing from secondary servers, the local `_status.json` is stale (it only reflects the primary server's progress). Update it to reflect the full dataset:

```python
import os, json

path = 'data/codal'
files = [f for f in os.listdir(path) if f.endswith('.json') and f not in ('_status.json',)]
status = {'processed': sorted([f.replace('.json','') for f in files]),
          'ok': len(files), 'err': 0}
with open(os.path.join(path, '_status.json'), 'w') as f:
    json.dump(status, f, ensure_ascii=False)
```

### 3. Verify Completeness

Cross-reference against the stock universe to confirm only permanent gaps remain:

```python
import os, csv

local = {f.replace('.json','') for f in os.listdir('data/codal/')
         if f.endswith('.json') and f not in ('_status.json',)}

with open('data/stock_universe.csv', newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    universe = {r['ticker'] for r in reader}

missing = universe - local
perm_gaps = {'اسفراین', 'تادیکو', 'سلیمان'}
real_missing = missing - perm_gaps

if not real_missing:
    print(f"✅ Complete: {len(local)}/{len(universe)} stocks collected")
    print(f"  3 permanent gaps confirmed absent")
```

### 4. Targeted Re-parse (Improve Coverage Without New API Calls)

After verifying completeness, if field-level coverage shows gaps (parser missed some labels in already-downloaded HTML files), do a **targeted re-parse** instead of re-running the full pipeline:

1. **Identify gap stocks** — e.g., stocks with `has_revenue but not has_cogs`
2. **Fix the parser** — Most common fix: normalize Arabic Alef Maksura (`ى`→`ی`) and Persian commas (`،`→space)
3. **Re-parse only existing HTML files** — No API calls needed since raw HTML is cached

```python
for ticker in gap_stocks:
    data = json.load(open(f'data/codal/{ticker}.json'))
    changed = False
    for yk in list(data['years'].keys()):
        if 'cogs' in data['years'][yk]: continue
        parts = yk.split('/')
        hf = f'{ticker}_{parts[0]}_{parts[1]}_{parts[2]}.html'
        fp = f'data/codal/raw/{ticker}/{hf}'
        if not os.path.exists(fp): continue
        result = improved_parse(open(fp).read())
        if 'cogs' in result:
            data['years'][yk]['cogs'] = result['cogs']
            changed = True
    if changed:
        json.dump(data, open(f'data/codal/{ticker}.json', 'w'), ensure_ascii=False)
```

**Why this works**: The pipeline saves raw HTML alongside parsed JSON. A targeted re-parse costs zero API calls — it just re-runs extraction logic on cached files. A real session recovered +452 COGS, +651 SGA, and +640 interest values this way.

See `references/post-pipeline-quality-check.md` § "Targeted Re-parse: No API Calls Needed" for the full pattern.

### 5. Archive to Google Drive

### Pitfalls

- **`_status.json` is created by the pipeline script, not auto-updated** — it's written once at script start and only occasionally during the run. After rsyncing from multiple servers, it will be wildly inaccurate (e.g., `ok: 54` when 371 files exist). Always regenerate it after the final sync.
- **Don't use `--delete` on secondary servers** — When rsyncing from non-primary servers, omit `--delete` to avoid wiping files from other servers' ranges. Only the primary server (which has the broadest range or the full dataset) should use `--delete`.
- **No loose HTML files after organization** — After moving all HTML into per-company dirs, verify with `ls data/codal/raw/*.html | wc -l` — should return 0.
- **Company directories ≠ stock count** — There may be 408 company dirs but 406 stock JSONs. Some CODAL-only entities (not in the stock universe) may have HTML but no corresponding JSON.

## Pitfalls

- **Status check script must be on EVERY server** — The monitoring script SSHs into each fleet server and runs `python3 /tmp/status_check.py` to get progress. If this script is missing (forgotten during deployment), the check silently reports `0|0|0|ERR|?` for that server — making it look like zero throughput while the pipeline actually runs fine. Deploy the status check script to EVERY server at setup time, **including the primary server** whose code you're developing on. Without it, that server's progress looks like a stuck pipeline.
- **Geo-restriction** — Codal.ir is only accessible from inside Iran. All API calls (search.codal.ir, www.codal.ir, excel.codal.ir) are geo-blocked. The TSETMC CDN at cdn.tsetmc.com/api/Codal/ works globally as an alternative for report discovery.
- **Main site (www.codal.ir) broken** — As of July 2026, ALL subpages of www.codal.ir (Search.aspx, ReportList.aspx, Decision.aspx, CompanyInfo.aspx) return an ASP.NET error page: "خطای ناشناخته‌ای رخ داده است" (An unknown error has occurred). Only the home page and ContactUs.aspx work. This is a server-side issue, not a rate limit. The search API (search.codal.ir) still works independently.
- **Rate limiting (429)** — The search API returns 429 after ~35-45 requests at 1s intervals. The entire subdomain blocks simultaneously. The 429 can persist for HOURS (not minutes). Exponential backoff is required up to 600s+. The DDoS captcha endpoint returns 404. Use excel.codal.ir (separate domain) to download known filings while search is blocked.
- **API defaults to XML, but returns JSON with proper Accept header** — The v2/q and v1/financialYears endpoints return XML with Microsoft namespaces by default (no Accept header). Always set `Accept: application/json` in request headers. Without it, `json.loads()` fails. Legacy endpoints (v1/companies, etc.) return JSON regardless.
- **No pagination metadata** — The v2/q response only has Total and Page — no PageSize or TotalPages. The default page size is 20. The Length parameter is NOT a page size — it filters by financial period length in months (1-12).
- **Jalali dates only** — All dates in the API are Jalali (Persian) strings. The `financialYears` endpoint returns around 10 years of fiscal year-end dates.
- **Symbol encoding** — Persian symbols in URLs must be URL-encoded. Some symbols have leading spaces (e.g., `" آذرنگین"`). The API handles this correctly with URL encoding.
- **Empty search results** — Some combinations of filters return no results. The `IsAttacker` field in the response will be `true` if the request was flagged as suspicious.
- **`name` param is fuzzy, not exact** — Searching with `name=فولاد مبارکه اصفهان` matches ANY company that contains those words in its name, returning results from hundreds of unrelated companies across all industries. To filter to a single company, use `Symbol` with the ticker symbol (e.g., `Symbol=فولاد`), or combine `name` with additional filters.
- **Parent company vs subsidiary reports** — When searching by Symbol, the API returns filings from ALL entities that share that symbol, including subsidiaries. The parent company's own annual financial statements have **consolidated (تلفیقی) titles with no parenthetical company name**, e.g. `"صورت‌های مالی تلفیقی سال مالی منتهی به ۱۴۰۳/۱۲/۳۰ (حسابرسی شده)"`. Subsidiary reports append `(شرکت ...)` in the title. The parent company's annual reports are typically buried far from page 1 — for فولاد with 1447 filings across 73 pages, the parent's annual 1403 report appeared on page 10, 1402 on page 18, 1401 on page 26, 1400 on page 34.
- **Annual report publication timing** — Under Iranian regulations, companies must publish audited annual financial statements within 4 months of the fiscal year-end (i.e., by end of Ordibehesht for fiscal year ending 12/29). If searching for the latest annual report for 1404 and it's not found, it may not yet be published.
- **Range overlap in multi-server fleets** — Running the pipeline script WITHOUT args means it processes ALL stocks (start_idx=0, no limit), overlapping every other server's range. Always specify `<limit> <start_idx>` for each server. Detect unbounded processes via `ps aux | grep python` — no numbers after the script name means unbounded. Fix by killing the screen and restarting with explicit args (already-done stocks are skipped automatically). See `references/large-scale-pipeline-example.md` §Fleet Argument Pitfall.
- **`rsync --delete` on secondary servers wipes primary's data** — When syncing from multiple servers to one local directory, only use `--delete` on the primary server. Secondary servers use plain `rsync -az` (no `--delete`) — they only have a subset of stocks and `--delete` would remove the primary's files. See `references/large-scale-pipeline-example.md` §Rsync `--delete` Danger.
- **Stale output files from previous universe sizes inflate progress** — When the stock universe is redistributed (e.g., a server's allocation shrinks from 100 stocks to 55), old JSON files from the previous larger run persist in the output directory. The monitoring script counts ALL `.json` files, not just ones matching the current universe. This produces inflated percentages (e.g., 103% = 422/409) because old files are counted. **Detection** — use `comm` for precision triage:

```bash
# On the affected server:
python3 -c 'import json; [print(x["ticker"]) for x in json.load(open("your_stock_universe_file"))["universe"]]' \
  | sort > /tmp/universe_tickers.txt
ls /tmp/pipeline_results/*.json 2>/dev/null | grep -v "_status\|raw" \
  | xargs -I{} basename {} .json | sort > /tmp/output_tickers.txt

echo "✅ Overlap (in current universe + done): $(comm -12 /tmp/universe_tickers.txt /tmp/output_tickers.txt | wc -l)"
echo "🗑️ Stale (NOT in current universe):     $(comm -13 /tmp/universe_tickers.txt /tmp/output_tickers.txt | wc -l)"
echo "⏳ Pending (in universe, not yet done):  $(comm -23 /tmp/universe_tickers.txt /tmp/output_tickers.txt | wc -l)"
```

A large "Stale" count confirms inflation. **Fix**: Kill the pipeline, clean the output directory, and restart:

```bash
pkill -f 'your-extraction-script'
rm -rf /tmp/pipeline_results
mkdir -p /tmp/pipeline_results/raw
screen -dmS pipeline-session bash -c 'python3 /tmp/your-extraction-script <limit> <start_idx> 2>&1 | tee /tmp/pipeline.log'
```

**Important**: If some stocks from the CURRENT universe were already processed ("Overlap" column), nuking the full directory forces re-processing those stocks. This is acceptable since the pipeline's idempotency means re-downloads produce the same data. If you want to preserve existing work during cleanup, copy the overlapping files to a temp dir before nuking, then restore them after `mkdir`:

```bash
mkdir -p /tmp/codal_backup
for ticker in $(comm -12 /tmp/universe_tickers.txt /tmp/output_tickers.txt); do
  cp /tmp/pipeline_results/${ticker}.json /tmp/codal_backup/ 2>/dev/null
done
# ... rm -rf /tmp/pipeline_results; mkdir -p /tmp/pipeline_results/raw
cp /tmp/codal_backup/*.json /tmp/pipeline_results/ 2>/dev/null
```

The skip-done logic does NOT help here — stale files ARE the inflation source, they must be physically removed. Always verify the count after any universe redistribution.
- **Large company list** — The `v1/companies` endpoint returns 5,387+ entries (~400KB). Cache this response locally rather than re-fetching frequently.
- **Letter type IDs** — Letter type IDs are not consistent across publisher types. The same ID may have different meanings for different publisher types. Always use the `v1/categories` endpoint to get the correct mapping.
- **Excel URL** — The Excel service at `excel.codal.ir` returns **HTML tables** (Microsoft Office HTML format, NOT binary .xlsx). The response is `text/html` with 200-500KB of table markup. See `references/excel-html-format.md` for the table structure and parsing approach. The Excel download domain (`excel.codal.ir`) is NOT rate-limited alongside the search API — it continues to work even when `search.codal.ir` returns 429.\n- **TSETMC Codal proxy for report discovery** — `cdn.tsetmc.com/api/Codal/GetPreparedDataByInsCode/{n}/{insCode}` returns report metadata (tracingNo, dates, hasExcelReport flags) with no rate limiting and from anywhere in the world. Use this to discover which reports exist, then use the CODAL search API or Excel service to download the actual data. The proxy returns items with fields: `id`, `symbol`, `title`, `tracingNo`, `attachmentID`, `mainTableRowID`, `hasExcelReport` (1=yes), `hasHtmlReport` (2=available), `hasPDFReport` (2=available), `contentType` (10=financial statement). **Note**: The proxy does NOT return the LetterSerial needed for Excel download — you still need the CODAL search API (by TracingNo) to get the serial.\n- **Fipiran (fipiran.ir) as alternative** — The TSE's financial data warehouse (مرکز پردازش اطلاعات مالی ایران) has balance sheets and income statements via a REST API (`https://fipiran.ir/api/v1/`). Requires Bearer token authentication (registration with 3-day free trial). The API is nginx-protected (returns 403 without token).
- **Three tiers of CODAL stock data availability** — Not all CODAL-listed stocks have downloadable financial data. During a 409-stock pipeline, three distinct tiers emerged:\n  | Tier | Description | Count (observed) | Example |\n  |------|-------------|------------------|---------|\n  | **Tier 1: Full data** | FY listing + Excel reports return valid HTML with financial data | ~370/409 | فولاد, فملی |\n  | **Tier 2: FY listing only** | `v1/financialYears` returns FY dates, but ALL Excel endpoints return 404 for every year | ~2/409 | تادیکو, سلیمان |\n  | **Tier 3: No data at all** | `v1/financialYears` returns empty `[]` — stock is listed but no filings on CODAL | ~1/409 | اسفراین |\n  **Retry strategy**: Tier 2 (FY listing + all 404) and Tier 3 (no FYs) are permanent gaps — retrying won't help. Only Tier 1 stocks that hit transient errors (timeouts, network issues) warrant retries. Detect Tier 2 by checking Excel endpoint status; if all years return 404, mark the stock permanently unavailable.\n- **Cron schedule format: `every 5m` vs bare `5m`** — When setting up a `no_agent` monitoring cron (`hermes cron create` with `--schedule`), use **`every 5m`** (not just `5m`) for a repeating schedule. A bare `5m` creates a `"once in 5m"` schedule that runs exactly once and stops, leaving the job in `completed` state. Using `every 5m` creates a true repeating schedule. Alternatively, use standard cron expressions like `*/5 * * * *` which also repeat correctly. This pitfall affects any long-running pipeline monitoring setup.

## Support Files

- `references/api-endpoints.md` — Complete endpoint catalog with request/response schemas
- `references/letter-types.md` — Complete letter type catalog across all 12 categories (~100+ IDs)
- `references/excel-html-format.md` — CODAL Excel HTML table structure: which table/index holds BS vs IS vs CF, key row labels, Persian number parsing recipe, and pitfalls
- `templates/python-client.py` — Full Python client with search, reference data, and report URL generation (stdlib only)
- `references/large-scale-pipeline-example.md` — Architecture and lessons from a real 409-stock CODAL pipeline running on a remote server via screen, with progress monitoring, ETA computation, and cron-delivered Telegram reports
- `references/codal-pipeline-progress-july-2026.md` — Live fleet status snapshot: per-server progress, SSH commands, offline handling, stock range assignments
- `references/post-pipeline-quality-check.md` — HTML-vs-JSON coverage verification AND how to fix parser coverage: Persian normalization, exclusion-based pattern rules, multi-table selection, handling binary Excel files, and reprocess procedure
- `references/binary-excel-recovery.md` — Recovery of legacy binary Excel files (years 1391-1396): detection, re-download procedure, FY/serial caching, screen deployment, cron monitoring
- `scripts/codal-progress-check.sh` — Bash script for `no_agent` cron monitoring: SSHs into the remote server, counts done stocks/FY records/raw files, checks screen session health, computes ETA with a progress bar. Schedule via `hermes cron create --no-agent --script codal-progress-check.sh --schedule 15m`