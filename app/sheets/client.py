"""Google Sheets client — reads and writes salon data sheets."""
import json
from functools import lru_cache
from typing import Any, Optional

import gspread
from google.oauth2.service_account import Credentials
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import get_settings
from app.utils.logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Expected sheet tab names
SHEET_FAQ = "FAQ"
SHEET_SERVICES = "Services"
SHEET_APPOINTMENTS = "Appointments"
SHEET_CUSTOMERS = "Customers"


class GoogleSheetsClient:
    """Thin async-friendly wrapper around gspread (sync under the hood)."""

    def __init__(self) -> None:
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._client: Optional[gspread.Client] = None

    def _connect(self) -> None:
        settings = get_settings()
        creds_data = settings.google_sheets_credentials
        if not creds_data:
            raise RuntimeError(
                "GOOGLE_SHEETS_CREDENTIALS_JSON is missing or invalid"
            )
        creds = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
        self._client = gspread.authorize(creds)
        self._spreadsheet = self._client.open_by_key(settings.google_sheet_id)
        logger.info("Connected to Google Sheets", sheet_id=settings.google_sheet_id)

    def _sheet(self, name: str) -> gspread.Worksheet:
        if self._spreadsheet is None:
            self._connect()
        try:
            return self._spreadsheet.worksheet(name)  # type: ignore[union-attr]
        except gspread.WorksheetNotFound:
            logger.error("Worksheet not found", sheet=name)
            raise

    # ─── FAQ ──────────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def get_faqs(self) -> list[dict[str, str]]:
        """Return all FAQ rows as [{question, answer}]."""
        ws = self._sheet(SHEET_FAQ)
        records = ws.get_all_records()
        logger.debug("Fetched FAQs", count=len(records))
        return [
            {"question": r.get("Question", ""), "answer": r.get("Answer", "")}
            for r in records
            if r.get("Question")
        ]

    # ─── Services ─────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def get_services(self) -> list[dict[str, Any]]:
        """Return all service rows."""
        ws = self._sheet(SHEET_SERVICES)
        records = ws.get_all_records()
        logger.debug("Fetched services", count=len(records))
        return [
            {
                "service": r.get("Service", ""),
                "price": r.get("Price", ""),
                "duration": r.get("Duration", ""),
                "availability": r.get("Availability", ""),
            }
            for r in records
            if r.get("Service")
        ]

    # ─── Appointments ─────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def get_appointments(self, phone: Optional[str] = None) -> list[dict[str, Any]]:
        """Return appointments, optionally filtered by phone."""
        ws = self._sheet(SHEET_APPOINTMENTS)
        records = ws.get_all_records()
        if phone:
            records = [r for r in records if str(r.get("Phone", "")) == phone]
        logger.debug("Fetched appointments", count=len(records), phone=phone)
        return records

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def create_appointment(self, row: dict[str, Any]) -> bool:
        """Append a new appointment row."""
        ws = self._sheet(SHEET_APPOINTMENTS)
        ws.append_row(
            [
                row.get("name", ""),
                row.get("phone", ""),
                row.get("service", ""),
                row.get("stylist", ""),
                row.get("date", ""),
                row.get("time", ""),
                row.get("status", "Confirmed"),
            ]
        )
        logger.info("Appointment created in Sheets", phone=row.get("phone"))
        return True

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def update_appointment_status(self, phone: str, date: str, status: str) -> bool:
        """Update the Status column for the matching appointment."""
        ws = self._sheet(SHEET_APPOINTMENTS)
        records = ws.get_all_records()
        for idx, row in enumerate(records, start=2):  # row 1 = header
            if str(row.get("Phone", "")) == phone and str(row.get("Date", "")) == date:
                # Status is column 7 (G)
                ws.update_cell(idx, 7, status)
                logger.info(
                    "Appointment status updated",
                    phone=phone,
                    date=date,
                    status=status,
                )
                return True
        logger.warning("Appointment not found for update", phone=phone, date=date)
        return False

    # ─── Customers ────────────────────────────────────────────────────────────

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def upsert_customer(self, row: dict[str, Any]) -> bool:
        """Insert or update a customer record in the Customers sheet."""
        ws = self._sheet(SHEET_CUSTOMERS)
        records = ws.get_all_records()
        phone = str(row.get("phone", ""))
        for idx, rec in enumerate(records, start=2):
            if str(rec.get("Phone", "")) == phone:
                ws.update(
                    f"A{idx}:G{idx}",
                    [[
                        phone,
                        row.get("name", rec.get("Name", "")),
                        row.get("preferred_stylist", rec.get("PreferredStylist", "")),
                        row.get("favorite_service", rec.get("FavoriteService", "")),
                        row.get("visit_count", rec.get("VisitCount", 0)),
                        row.get("last_visit", rec.get("LastVisit", "")),
                        row.get("notes", rec.get("Notes", "")),
                    ]],
                )
                logger.info("Customer record updated in Sheets", phone=phone)
                return True
        # Insert new row
        ws.append_row([
            phone,
            row.get("name", ""),
            row.get("preferred_stylist", ""),
            row.get("favorite_service", ""),
            row.get("visit_count", 0),
            row.get("last_visit", ""),
            row.get("notes", ""),
        ])
        logger.info("Customer record inserted in Sheets", phone=phone)
        return True


@lru_cache(maxsize=1)
def get_sheets_client() -> GoogleSheetsClient:
    return GoogleSheetsClient()
