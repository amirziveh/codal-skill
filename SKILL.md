---
name: codal
description: "Work with Codal (codal.ir) — the official Iranian corporate disclosure system. Search financial statements, auditor reports, board decisions, and other mandatory filings by Iran's capital market companies. Covers the search API, reference data, report detail pages, and file downloads."
version: 1.0.0
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
| **Search API** | `https://search.codal.ir/api/search/` | RESTful JSON API |
| **Main Site** | `https://www.codal.ir/` | ASP.NET WebForms site |
| **Excel Service** | `https://excel.codal.ir/service/Excel/` | Excel file downloads |
| **DDoS Protection** | `https://www.codal.ir/api/ddos/v1/` | Captcha service (rate limit protection) |

### Geo-restriction

Codal.ir is geo-restricted and only accessible from inside Iran. All API calls must be routed through an Iran-based server. The `search.codal.ir` subdomain is also geo-restricted.

### Letter Serial

Every filing (letter) has a unique **LetterSerial** — a base64-like opaque string used to access the report page, PDF, Excel, and attachments (e.g. `VmoA3IWcyPnuPOmTzoJjaA%3d%3d`).

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
All 5,387+ companies listed in the Codal system.

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
| `Length` | int | Results per page (-1 = all) |
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

### Captcha / Rate Limiting

The API has DDoS protection that triggers at **429 Too Many Requests**. When triggered:

1. `POST https://www.codal.ir/api/ddos/v1/begin` with `{"clientId": "ABBS"}`
   → Returns `{"CaptchaToken": "..."}`

2. User solves the captcha image (fetched from the token)

3. `POST https://www.codal.ir/api/ddos/v1/end` with `{"CaptchaToken": "...", "Captchatext": "..."}`
   → Returns success/failure

The captcha service has a timeout (CAPTCHA_TIMEOUT_MS) and max retries (MAX_RETRIES).

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

### Workflow 1: Search for Letters by Symbol

```python
import urllib.request, json

def search_codal(symbol: str, page: int = 1, length: int = 20) -> dict:
    """Search for filings by company symbol."""
    url = f"https://search.codal.ir/api/search/v2/q?Symbol={urllib.parse.quote(symbol)}&PageNumber={page}&Length={length}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Find all filings for فولاد
results = search_codal("فولاد", length=5)
print(f"Total: {results['Total']}")
for letter in results['Letters']:
    print(f"  [{letter['TracingNo']}] {letter['Title'][:60]}...")
    print(f"    Sent: {letter['SentDateTime']}")
    print(f"    PDF: {letter['PdfUrl']}")
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
    """
    params = {
        "Symbol": symbol,
        "LetterType": str(letter_type),
        "Length": "20",
        "PageNumber": "1",
    }
    params.update(extra)
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"https://search.codal.ir/api/search/v2/q?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# Example: Get monthly reports for فولاد
monthly = search_by_letter_type("فولاد", 58)
for letter in monthly['Letters']:
    print(f"{letter['YearEndToDate']}: {letter['Title'][:80]}")
```

### Workflow 4: Get Financial Years

```python
def get_financial_years(symbol: str) -> list[str]:
    """Get fiscal year-end dates for a company (Jalali format)."""
    url = f"https://search.codal.ir/api/search/v1/financialYears?Symbol={urllib.parse.quote(symbol)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

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
    """Search filings within a date range. Dates are Jalali (e.g., '1405/01/01')."""
    params = {"Symbol": symbol, "FromDate": from_date, "ToDate": to_date, "Length": "50", "PageNumber": "1"}
    params.update(extra)
    query = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"https://search.codal.ir/api/search/v2/q?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# All filings for فولاد in Q1 1405
q1 = search_by_date_range("فولاد", "1405/01/01", "1405/03/31")
```

## Pitfalls

- **Geo-restriction** — Codal.ir is only accessible from inside Iran. All API calls (`search.codal.ir`, `www.codal.ir`, `excel.codal.ir`) are geo-blocked. Use an Iran-based proxy or server.
- **Rate limiting (429)** — The API returns HTTP 429 when too many requests are made. You must then solve a captcha via the DDoS API (`/api/ddos/v1/begin` + `/api/ddos/v1/end`). Use 0.5-1s delays and limit concurrent requests.
- **No pagination metadata** — The `v2/q` response only has `Total` and `Page` — no `PageSize` or `TotalPages`. The `Length` parameter controls page size (default browser behavior: 20 per page).
- **Jalali dates only** — All dates in the API are Jalali (Persian) strings. The `financialYears` endpoint returns around 10 years of fiscal year-end dates.
- **Symbol encoding** — Persian symbols in URLs must be URL-encoded. Some symbols have leading spaces (e.g., `" آذرنگین"`). The API handles this correctly with URL encoding.
- **Empty search results** — Some combinations of filters return no results. The `IsAttacker` field in the response will be `true` if the request was flagged as suspicious.
- **Serial expiration** — LetterSerial values may expire. If a report page returns an error, the serial may be stale or the letter may have been removed.
- **Large company list** — The `v1/companies` endpoint returns 5,387+ entries (~400KB). Cache this response locally rather than re-fetching frequently.
- **Letter type IDs** — Letter type IDs are not consistent across publisher types. The same ID may have different meanings for different publisher types. Always use the `v1/categories` endpoint to get the correct mapping.
- **Excel URL** — The Excel service at `excel.codal.ir` may have different geo-restriction rules than the main site. It returns Excel binary data (.xlsx) directly.

## Support Files

- `references/api-endpoints.md` — Complete endpoint catalog with request/response schemas
- `references/letter-types.md` — Complete letter type catalog across all 12 categories (~100+ IDs)
- `templates/python-client.py` — Full Python client with search, reference data, and report URL generation (stdlib only)