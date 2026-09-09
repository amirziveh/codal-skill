# CODAL Excel HTML Format — Financial Statement Data Extraction

## What the "Excel Download" Actually Returns

The endpoint `https://excel.codal.ir/service/Excel/GetAll/{serial}/0` does NOT return a binary `.xlsx` file. It returns an **HTML document** with Microsoft Office Excel namespaces — an HTML table formatted for Excel to open. The response is `text/html`, ~200-500KB.

This is actually easier to parse than binary Excel. No libraries needed — regex on HTML works reliably.

## Which Table to Use for Factor Construction

**Use the Separate (Parent) Company Statements (Tables 5-7), NOT the consolidated statements (Tables 0-2).**

The consolidated statements include subsidiaries' financials and minority interests which distort per-stock metrics. The separate statements reflect the issuing company's own equity, which is what the stock represents.

For Book Equity, "جمع حقوق صاحبان سهام" in the consolidated statement (Table 0) includes minority interest (سهم اقلیت). In the separate statement (Table 5), it's strictly the parent company's equity. The standard factor methodology requires the parent's equity.

### Recommended:

| Variable | Table | Row Label |
|----------|-------|-----------|
| Total Assets | **5** (separate BS) | جمع دارایی‌ها |
| Book Equity | **5** (separate BS) | جمع حقوق صاحبان سهام |
| Revenue | **7** (separate IS) | درآمدهای عملیاتی |
| COGS | **7** (separate IS) | بهای تمام شده درآمدهای عملیاتی |
| SG&A | **7** (separate IS) | هزینه‌های فروش، اداری و عمومی |
| Interest Expense | **7** (separate IS) | هزینه‌های مالی |
| Net Income | **7** (separate IS) | سود (زیان) خالص |

Known issue: the EXACT title may differ between tables — Table 0 might have "جمع حقوق صاحبان سهام" while Table 5 has the same title. The cell-matching code already handles this since it searches by content across ALL tables and takes the largest match.

## Row Structure

### Table 0: Balance Sheet (dual-column format)

Each row has 8 cells: `[item_L, cur_yr_L, prev_yr_L, chg%_L, item_R, cur_yr_R, prev_yr_R, chg%_R]`

Assets on the left, Liabilities+Equity on the right.

**Key rows to extract:**
- `جمع دارایی‌ها` — **Total Assets** (cur_yr value at cell index +1)
- `جمع حقوق صاحبان سهام` — **Total Equity** / Book Equity
- `جمع بدهی‌ها` — Total Liabilities

### Table 2: Income Statement (single-column format)

Each row has 4 cells: `[item, cur_yr, prev_yr, chg%]`

**Key rows to extract:**
- `درآمدهای عملیاتی` — **Revenue** (فروش)
- `بهای تمام شده درآمدهای عملیاتی` — **COGS** (note: always negative in parentheses)
- `سود (زیان) ناخالص` — **Gross Profit**
- `هزینه‌های فروش، اداری و عمومی` — **SG&A**
- `سود (زیان) عملیاتی` — **Operating Profit**
- `هزینه‌های مالی` — **Interest Expense**
- `سود (زیان) خالص` — **Net Income** (first non-zero non-header row)

## Persian Number Format

Numbers use:
- **Persian digits**: `۰۱۲۳۴۵۶۷۸۹` — translate via `str.maketrans()`
- **Thousand separators**: commas between digit groups (e.g., `۳۳۹,۱۹۷,۳۹۹`)
- **Negatives**: parentheses, not minus signs (e.g., `(۱۶۶,۷۴۱,۰۸۰)`)
- **Zero values**: rendered as `۰`
- **N/A**: rendered as `--`

## Parsing Recipe (Python stdlib)

```python
import re

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

def parse_number(s: str) -> float:
    s = s.strip()
    if not s or s == '--': return 0.0
    neg = -1 if s.startswith('(') and s.endswith(')') else 1
    if neg == -1: s = s[1:-1]
    s = s.translate(PERSIAN_DIGITS).replace(',', '')
    try: return float(s) * neg
    except: return 0.0

def parse_financials(html: str) -> dict:
    """Extract key financial items from CODAL Excel HTML."""
    tables = re.findall(r"<table[^>]*>(.*?)</table>", html, re.DOTALL)
    result = {}
    for table in tables:
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.DOTALL)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            texts = [re.sub(r"<.*?>", "", c).strip() for c in cells]
            if not any(texts): continue
            for ci, ct in enumerate(texts):
                if not ct: continue
                nxt = texts[ci+1] if ci+1 < len(texts) else ""
                v = parse_number(nxt)
                if v == 0.0: continue
                if ct == "جمع دارایی\u200cها": result["total_assets"] = v
                elif ct == "جمع حقوق صاحبان سهام": result["total_equity"] = v
                elif ct == "درآمدهای عملیاتی" and v > 0: result["revenue"] = v
                elif "بهای تمام" in ct and "شده" in ct and "درآمد" in ct:
                    result["cogs"] = abs(v)
                elif "هزینه" in ct and "فروش" in ct and "اداری" in ct:
                    result["sga"] = abs(v)
                elif ct == "هزینه\u200cهای مالی": result["interest"] = abs(v)
                elif "سود (زیان) عملیاتی" in ct: result["op_profit"] = v
                elif ct in ("سود (زیان) خالص", "سود خالص") and v != 0:
                    if "net_income" not in result or abs(v) > abs(result.get("net_income", 0)):
                        result["net_income"] = v
    return result
```

## Pitfalls

- The same text label may appear in MULTIPLE tables (both consolidated and separate). The consolidated tables (0, 2) come first in the HTML document and should be preferred.
- Some cells have zero-width non-joiners (U+200C) in the text which can break simple string matching. Use `in` operator with partial matches rather than `==`.
- The "سود (زیان) خالص" (Net Income) row appears 3-4 times in each table (header row, calculated line, attribution lines). Take the first non-zero value.
- COGS is always shown as negative (in parentheses). Store as absolute value.
- Interest expense includes ALL financial costs (bank charges, Islamic financing costs).
- For banks and insurance companies, some income statement line items may use different labels. The basic structure is the same.
