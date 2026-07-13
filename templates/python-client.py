"""Codal API Client — Iranian Corporate Disclosure System

A complete Python client for the Codal (codal.ir) search API using only stdlib.

Usage:
    client = CodalClient()
    letters = client.search(symbol="فولاد", length=5)
    for l in letters:
        print(f"[{l['TracingNo']}] {l['Title'][:60]}")
"""

import json
import time
import urllib.parse
import urllib.request
from typing import Any, Optional

API_BASE = "https://search.codal.ir/api/search/"
CODAL_BASE = "https://www.codal.ir"
EXCEL_BASE = "https://excel.codal.ir/service/Excel"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}


class CodalClient:
    """Client for the Codal search API."""

    def __init__(self, delay: float = 0.3):
        self.delay = delay  # seconds between calls to avoid rate limiting
        self._companies: Optional[list[dict]] = None

    def _get(self, url: str) -> Any:
        """Make a GET request with rate limiting."""
        time.sleep(self.delay)
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    # ── Reference Data ──────────────────────────────────────────────

    def get_companies(self, force_refresh: bool = False) -> list[dict]:
        """Get all companies (cached after first call). ~5,387 entries."""
        if self._companies is not None and not force_refresh:
            return self._companies
        self._companies = self._get(API_BASE + "v1/companies")
        return self._companies

    def get_categories(self) -> list[dict]:
        """Get letter type taxonomy: categories → publisher types → letter types."""
        return self._get(API_BASE + "v1/categories")

    def get_industry_groups(self) -> list[dict]:
        """Get industry groups."""
        return self._get(API_BASE + "v1/IndustryGroup")

    def get_auditors(self) -> list[dict]:
        """Get auditor firms."""
        return self._get(API_BASE + "v1/auditors")

    def get_financial_years(self, symbol: str = "") -> list[str]:
        """Get fiscal year-end dates for a company."""
        url = API_BASE + "v1/financialYears"
        if symbol:
            url += f"?Symbol={urllib.parse.quote(symbol)}"
        return self._get(url)

    # ── Search ──────────────────────────────────────────────────────

    def search(self, **params) -> list[dict]:
        """Search for letters/filings.

        Common params:
            symbol (str): Company symbol (e.g., "فولاد")
            subject (str): Text search in subject
            letter_type (int): Letter type ID (e.g., 58 for monthly report)
            from_date (str): Jalali start date (YYYY/MM/DD)
            to_date (str): Jalali end date (YYYY/MM/DD)
            page (int): Page number (default: 1)
            length (int): Results per page (default: 20, -1 for all)
            company_state (int): 0=Bourse, 1=Fara Bourse, -1=all
            category (int): Category ID
            audited (bool): Include audited reports only
        """
        # Map Python-friendly names to API param names
        param_map = {
            "symbol": "Symbol",
            "subject": "Subject",
            "tracing_no": "TracingNo",
            "letter_code": "LetterCode",
            "letter_type": "LetterType",
            "from_date": "FromDate",
            "to_date": "ToDate",
            "isic": "Isic",
            "auditor_ref": "AuditorRef",
            "year_end": "YearEndToDate",
            "page": "PageNumber",
            "length": "Length",
            "audited": "Audited",
            "not_audited": "NotAudited",
            "childs": "Childs",
            "mains": "Mains",
            "publisher": "Publisher",
            "company_state": "CompanyState",
            "reporting_type": "ReportingType",
            "name": "name",
            "category": "Category",
            "company_type": "CompanyType",
            "consolidatable": "Consolidatable",
            "not_consolidatable": "NotConsolidatable",
            "industry_group": "IndustryGroup",
        }

        query_params = {}
        for py_name, api_name in param_map.items():
            if py_name in params and params[py_name] is not None:
                val = params[py_name]
                if isinstance(val, bool):
                    val = str(val).lower()
                query_params[api_name] = str(val)

        # Default page if not specified
        if "PageNumber" not in query_params:
            query_params["PageNumber"] = "1"
        if "Length" not in query_params:
            query_params["Length"] = "20"

        query = urllib.parse.urlencode(query_params)
        url = API_BASE + f"v2/q?{query}"
        result = self._get(url)
        return result.get("Letters", [])

    def search_all(self, **params) -> list[dict]:
        """Search all pages and return all results."""
        all_letters = []
        page = 1
        while True:
            params["page"] = page
            letters = self.search(**params)
            if not letters:
                break
            all_letters.extend(letters)
            if len(letters) < int(params.get("length", 20)):
                break
            page += 1
        return all_letters

    # ── Report URLs ─────────────────────────────────────────────────

    @staticmethod
    def get_letter_serial(letter: dict) -> str:
        """Extract and decode LetterSerial from a letter's Url field."""
        url = letter["Url"]
        serial = url.split("LetterSerial=")[1].split("&")[0]
        return urllib.parse.unquote(serial)

    @staticmethod
    def get_report_url(serial: str, letter_type: int = 0) -> dict:
        """Get all URLs for a specific filing."""
        encoded = urllib.parse.quote(serial, safe="")
        return {
            "html": f"{CODAL_BASE}/Reports/Decision.aspx?LetterSerial={encoded}&rt=0&let={letter_type}&ct=0&ft=-1",
            "pdf": f"{CODAL_BASE}/DownloadFile.aspx?hs={encoded}&ft=1005&let={letter_type}",
            "excel": f"{EXCEL_BASE}/GetAll/{encoded}/0",
            "attachment": f"{CODAL_BASE}/Reports/Attachment.aspx?LetterSerial={encoded}",
        }

    # ── Utilities ───────────────────────────────────────────────────

    def search_by_symbol(self, symbol: str, length: int = 20) -> list[dict]:
        """Simple search by company symbol."""
        return self.search(symbol=symbol, length=length)

    def search_by_letter_type(self, symbol: str, letter_type: int, **extra) -> list[dict]:
        """Search for specific letter types for a company."""
        return self.search(symbol=symbol, letter_type=letter_type, **extra)

    def search_by_date_range(self, symbol: str, from_date: str, to_date: str, **extra) -> list[dict]:
        """Search filings within a date range (Jalali dates: YYYY/MM/DD)."""
        return self.search(symbol=symbol, from_date=from_date, to_date=to_date, **extra)

    def get_annual_reports(self, symbol: str) -> list[dict]:
        """Get annual financial statements (letter type 6)."""
        return self.search_by_letter_type(symbol, 6)

    def get_monthly_reports(self, symbol: str) -> list[dict]:
        """Get monthly performance reports (letter type 58)."""
        return self.search_by_letter_type(symbol, 58)

    def get_board_decisions(self, symbol: str) -> list[dict]:
        """Get board decisions and meeting results."""
        return self.search(
            symbol=symbol,
            category=6,  # آگهی دعوت به مجامع و تصمیمات
            length=20,
        )

    def get_capital_increases(self, symbol: str) -> list[dict]:
        """Get capital increase announcements."""
        return self.search(
            symbol=symbol,
            category=7,  # افزایش سرمایه
            length=20,
        )


# ── Example Usage ─────────────────────────────────────────────────

if __name__ == "__main__":
    client = CodalClient(delay=0.5)

    # 1. Get reference data
    print("=== Companies ===")
    companies = client.get_companies()
    print(f"Total: {len(companies)}")
    # Find فولاد
    for c in companies:
        if c["sy"].strip() == "فولاد":
            print(f"  Found: {c['sy']} — {c['n']} (ISIC: {c['i']}, IG: {c['IG']})")
            break

    print("\n=== Categories ===")
    cats = client.get_categories()
    for cat in cats[:3]:
        print(f"  [{cat['Code']}] {cat['Name']}")

    print("\n=== Industry Groups ===")
    igs = client.get_industry_groups()
    print(f"Total: {len(igs)}")

    print("\n=== Financial Years for فولاد ===")
    years = client.get_financial_years("فولاد")
    print(f"  {years[:5]}")

    # 2. Search
    print("\n=== Recent filings for فولاد ===")
    letters = client.search(symbol="فولاد", length=5)
    for l in letters:
        serial = CodalClient.get_letter_serial(l)
        print(f"  [{l['TracingNo']}] {l['Title'][:70]}")
        print(f"    Published: {l['PublishDateTime']}")
        print(f"    HTML: {'✅' if l['HasHtml'] else '❌'} PDF: {'✅' if l['HasPdf'] else '❌'} Excel: {'✅' if l['HasExcel'] else '❌'}")
        urls = CodalClient.get_report_url(serial, 6)
        print(f"    PDF: {urls['pdf'][:80]}...")
        print()