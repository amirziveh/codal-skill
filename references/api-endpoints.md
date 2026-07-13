# Codal API Endpoint Reference

**Base URL**: `https://search.codal.ir/api/search/`
**Main Site**: `https://www.codal.ir/`
**Excel Service**: `https://excel.codal.ir/service/Excel/`

All endpoints are geo-restricted (Iran only).

---

## Reference Data Endpoints

### `GET v1/companies`
Return all companies registered in the Codal system.

**Response**: `list[Company]`

| Field | Name | Type | Description |
|-------|------|------|-------------|
| `sy` | نماد | string | Ticker symbol (e.g., `فولاد`) |
| `n` | نام | string | Company name |
| `i` | ISIC | string | ISIC industry code |
| `t` | نوع | int | Company type (-1 = unknown) |
| `st` | وضعیت | int | Company state (0=Bourse, 1=Fara Bourse, 2=Registered, 3=Not registered) |
| `IG` | گروه صنعت | int | Industry group ID |
| `RT` | نوع گزارشگری | int | Reporting type code |

**Count**: ~5,387 companies

---

### `GET v1/categories`
Return the letter type taxonomy: 12 categories → 6 publisher types → letter types.

**Response**: `list[Category]`

```json
{
  "Code": -1,
  "Name": "همه موارد",
  "PublisherTypes": [
    {"Code": 1, "Name": "ناشران", "LetterTypes": [{"Id": 6, "Name": "اطلاعات و صورتهای مالی میاندوره ای"}, ...]},
    {"Code": 2, "Name": "کارگزاران", "LetterTypes": []},
    {"Code": 3, "Name": "نهاد مالی", "LetterTypes": []},
    {"Code": 4, "Name": "نهاد عمومی", "LetterTypes": []},
    {"Code": 5, "Name": "شرکت دولتي", "LetterTypes": []},
    {"Code": 17, "Name": "شرکتهای بخش عمومی و سایر", "LetterTypes": []}
  ]
}
```

Categories (12 total):
| Code | Name |
|------|------|
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

---

### `GET v1/IndustryGroup`
Return industry groups.

**Response**: `list[{Id: int, Name: str}]`

**Count**: ~72 industry groups

Example: `{"Id": 27, "Name": "فلزات اساسی"}`

---

### `GET v1/auditors`
Return auditor firms.

**Response**: `list[{n: str (name), c: str (code)}]`

**Count**: ~197 auditors

Example: `{"n": "موسسه حسابرسي آزمون پرداز", "c": "..."}`

---

### `GET v1/financialYears?Symbol={symbol}`
Return fiscal year-end dates for a specific company.

**Params**: `Symbol` — company symbol (optional but recommended)

**Response**: `list[str]` — Jalali date strings (e.g., `["1405/12/29", "1404/12/29", ...]`)

Returns ~10 fiscal years per company.

---

## Search Endpoint

### `GET v2/q?{params}`
Search for letters/filings with full filter capability.

**Response**: `{Total: int, Page: int, Letters: list[Letter], IsAttacker: bool}`

#### Letter Schema
```json
{
  "TracingNo": 1563609,
  "Symbol": "فولاد",
  "CompanyName": "فولاد مبارکه اصفهان",
  "UnderSupervision": 0,
  "Title": "عنوان نامه",
  "LetterCode": "ن-۱۰",
  "SentDateTime": "۱۴۰۵/۰۴/۲۲ ۱۲:۲۶:۳۱",
  "PublishDateTime": "۱۴۰۵/۰۴/۲۲ ۱۲:۲۶:۳۱",
  "HasHtml": true,
  "HasExcel": true,
  "HasPdf": true,
  "HasXbrl": false,
  "HasAttachment": true,
  "IsEstimate": false,
  "Url": "/Reports/Decision.aspx?LetterSerial=VmoA3IWcyPnuPOmTzoJjaA%3d%3d&rt=0&let=6&ct=0&ft=-1",
  "PdfUrl": "DownloadFile.aspx?hs=VmoA3IWcyPnuPOmTzoJjaA%3d%3d&ft=1005&let=6",
  "ExcelUrl": "https://excel.codal.ir/service/Excel/GetAll/VmoA3IWcyPnuPOmTzoJjaA%3d%3d/0",
  "XbrlUrl": "",
  "AttachmentUrl": "/Reports/Attachment.aspx?LetterSerial=VmoA3IWcyPnuPOmTzoJjaA%3d%3d",
  "TedanUrl": "http://www.tedan.ir",
  "SuperVision": {
    "UnderSupervision": 3,
    "AdditionalInfo": "",
    "Reasons": ["بررسی وضعیت شفافیت اطلاعاتی ناشر"]
  }
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| `TracingNo` | int | Unique filing ID (پیگیری) |
| `Symbol` | string | Company symbol |
| `CompanyName` | string | Company full name |
| `UnderSupervision` | int | Under supervision flag |
| `Title` | string | Filing title (Persian) |
| `LetterCode` | string | Letter reference code |
| `SentDateTime` | string | Sent date (Jalali: `YYYY/MM/DD HH:MM:SS`) |
| `PublishDateTime` | string | Published date (Jalali) |
| `HasHtml` | bool | Has HTML report page |
| `HasExcel` | bool | Has Excel download |
| `HasPdf` | bool | Has PDF download |
| `HasXbrl` | bool | Has XBRL format |
| `HasAttachment` | bool | Has additional attachments |
| `IsEstimate` | bool | Is an estimate (پیش‌بینی) |
| `Url` | string | Report page path |
| `PdfUrl` | string | PDF download path |
| `ExcelUrl` | string | Excel download URL |
| `XbrlUrl` | string | XBRL URL (often empty) |
| `AttachmentUrl` | string | Attachment page path |
| `TedanUrl` | string | Tedan (تادن) URL |
| `SuperVision` | object | Supervision info |

---

## Report Detail Page

`GET https://www.codal.ir/Reports/Decision.aspx?LetterSerial={serial}&rt=0&let={letterType}&ct=0&ft=-1`

ASP.NET WebForms page with full financial statements rendered as HTML. Available data:

- **Company Info**: Name, symbol, registered capital, ISIC, fiscal year end
- **Report Info**: Period (12-month), audit status, period end date
- **Financial Statements**: Balance sheet, income statement, cash flow, equity changes (selectable via dropdown)
- **Auditor Report**: Opinion, scope, key audit matters, signers
- **Signers**: Name, membership number, position, signature timestamp

Optional English version: Add `&lng=en-us` to URL.

---

## File Downloads

| File | URL | Notes |
|------|-----|-------|
| **PDF** | `/DownloadFile.aspx?hs={serial}&ft=1005&let={letterType}` | Full PDF of the filing |
| **Excel** | `https://excel.codal.ir/service/Excel/GetAll/{serial}/0` | Excel binary (.xlsx) all tables |
| **Attachment** | `/Reports/Attachment.aspx?LetterSerial={serial}` | Supporting documents |

To get the LetterSerial from a search result:
```python
serial = letter["Url"].split("LetterSerial=")[1].split("&")[0]
import urllib.parse
serial = urllib.parse.unquote(serial)  # decode %3d → =
```

---

## DDoS/Captcha API

**Note**: Only needed after receiving HTTP 429 responses.

### `POST https://www.codal.ir/api/ddos/v1/begin`
Request captcha challenge.

**Body**: `{"clientId": "ABBS"}`

**Response**: `{"CaptchaToken": "..."}`

### `POST https://www.codal.ir/api/ddos/v1/end`
Submit captcha solution.

**Body**: `{"CaptchaToken": "...", "Captchatext": "..."}`

**Response**: Success/failure

---

## Domain Summary

| Domain | Purpose | Protocol |
|--------|---------|----------|
| `search.codal.ir` | REST API (JSON) | HTTPS |
| `www.codal.ir` | Main website, report pages | HTTPS |
| `excel.codal.ir` | Excel file downloads | HTTPS |