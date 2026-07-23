"""Outlook .msg email extractor."""

import os
import re
import tempfile
from datetime import datetime
from typing import Optional, List

from models.rfq_data import RFQData, RFQItem
from extractors.base import BaseExtractor


class MSGExtractor(BaseExtractor):
    """Extracts RFQ data from Outlook .msg email files.

    Handles two main scenarios:
      1. Invitation emails (Petronas-style): metadata in body, data in attachments
      2. Direct inquiry emails (Alsharq-style): product details in body text
    """

    @staticmethod
    def can_handle(file_path: str) -> bool:
        return file_path.lower().endswith(".msg")

    def extract(self, file_path: str) -> RFQData:
        import extract_msg

        data = RFQData(source_file_path=file_path)
        msg = extract_msg.Message(file_path)

        subject = msg.subject or ""
        body = msg.body or ""
        data.raw_extracted_text = f"Subject: {subject}\n\n{body}"

        # ----- Extract metadata from email body -----
        data.closing_date = self._extract_closing_date(body)
        data.tender_subject = self._extract_tender_subject(body, subject)

        tender_no = self._extract_tender_number(body, subject)
        if tender_no:
            data.tender_number = tender_no
            data.include_tender_number = True

        end_user = self._extract_end_user(body)
        if end_user:
            data.end_user = end_user
            data.include_end_user = True

        # ----- Try to parse product items directly from body -----
        items = self._extract_items_from_body(body)
        if items:
            data.items = items

        # ----- Process attachments -----
        attachment_data = self._process_attachments(msg, file_path)
        if attachment_data:
            # Merge: attachment items take precedence if body had none
            if not data.items and attachment_data.items:
                data.items = attachment_data.items
            # Merge metadata — prefer attachment data for tender number
            if attachment_data.tender_number and not data.tender_number:
                data.tender_number = attachment_data.tender_number
                data.include_tender_number = True
            if attachment_data.closing_date and not data.closing_date:
                data.closing_date = attachment_data.closing_date
            # Append raw text
            if attachment_data.raw_extracted_text:
                data.raw_extracted_text += (
                    "\n\n=== FROM ATTACHMENTS ===\n"
                    + attachment_data.raw_extracted_text
                )

        # Auto-detect sections from combined text
        self._auto_detect_sections(data, body)

        msg.close()
        return data

    # ------------------------------------------------------------------
    # Closing date extraction
    # ------------------------------------------------------------------

    def _extract_closing_date(self, body: str) -> str:
        """Extract closing date from email body."""
        # Pattern: "NO later than 1 July 2026"
        m = re.search(
            r"NO\s+later\s+than\s+(\d{1,2}\s+\w+\s+\d{4})",
            body,
            re.IGNORECASE,
        )
        if m:
            return self._format_date(m.group(1).strip())

        # Pattern: "before April 30th, 2026"
        m = re.search(
            r"(?:before|by)\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})",
            body,
            re.IGNORECASE,
        )
        if m:
            return self._format_date(m.group(1).strip())

        # Pattern: "Closing Date: ASAP" or "Closing Date: 2026.07.01"
        m = re.search(
            r"(?:closing|deadline)\s*(?:date)?\s*[:\-]\s*([^\n.]+)",
            body,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()

        return ""

    def _format_date(self, date_str: str) -> str:
        """Try to format date string to YYYY.MM.DD."""
        # Remove ordinal suffixes
        clean = re.sub(r"(\d)(st|nd|rd|th)", r"\1", date_str)
        clean = clean.replace(",", "")

        for fmt in ("%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
            try:
                dt = datetime.strptime(clean.strip(), fmt)
                return dt.strftime("%Y.%m.%d")
            except ValueError:
                continue
        return date_str  # Return as-is if can't parse

    # ------------------------------------------------------------------
    # Tender subject / title
    # ------------------------------------------------------------------

    def _extract_tender_subject(self, body: str, subject: str) -> str:
        """Extract tender subject from body, fallback to email subject."""
        # Petronas-style: "Tender Title : PROVISION OF SUPPLY AND DELIVERY OF..."
        m = re.search(
            r"Tender\s+Title\s*:\s*"
            r"(?:PROVISION\s+OF\s+SUPPLY\s+AND\s+DELIVERY\s+OF\s+)?"
            r"(.+?)(?:\s+FOR\s+PETRONAS|\r|\n|$)",
            body,
            re.IGNORECASE,
        )
        if m:
            raw = m.group(1).strip()
            return " ".join(w.capitalize() for w in raw.split())

        # Direct inquiry style — use subject
        if subject:
            # Clean up email subject prefixes
            clean = re.sub(r"^(RE:|FW:|Fwd:)\s*", "", subject, flags=re.IGNORECASE)
            clean = re.sub(r"^REQ-\d+\s*-?\s*", "", clean).strip()
            if clean:
                return clean

        return ""

    # ------------------------------------------------------------------
    # Tender number
    # ------------------------------------------------------------------

    def _extract_tender_number(self, body: str, subject: str) -> str:
        """Extract external tender/RFQ number."""
        # Petronas pattern: "Tender No. : PCIHBV/2026/MRP/6115"
        m = re.search(
            r"Tender\s+No\.?\s*:\s*(\S+)", body, re.IGNORECASE
        )
        if m:
            return m.group(1).strip()

        # RFQ number in subject: "RFQ: PCIHBV/2026/MRP/6115"
        m = re.search(r"RFQ\s*:\s*(\S+)", subject, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        # REQ pattern: "REQ-00141231"
        m = re.search(r"(REQ-\d+)", subject, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        return ""

    # ------------------------------------------------------------------
    # End user
    # ------------------------------------------------------------------

    def _extract_end_user(self, body: str) -> str:
        """Try to extract end-user name from body."""
        # "our client «Name» issued a requirement"
        m = re.search(
            r"(?:client|customer)\s+[\"'\u00ab\u201c]([^\"'\u00bb\u201d]+)[\"'\u00bb\u201d]",
            body,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()

        # "End user: Name"
        m = re.search(r"End[\s-]*user\s*:\s*(.+)", body, re.IGNORECASE)
        if m:
            return m.group(1).strip()

        return ""

    # ------------------------------------------------------------------
    # Item extraction from email body
    # ------------------------------------------------------------------

    def _extract_items_from_body(self, body: str) -> List[RFQItem]:
        """Extract product items from email body text (Alsharq-style)."""
        items: List[RFQItem] = []

        # Pattern: multi-line product description followed by "Qty: N"
        # The Alsharq example has description lines then "Qty: 2"
        qty_match = re.search(r"Qty\s*[:\-]?\s*(\d+)", body, re.IGNORECASE)
        if not qty_match:
            return []

        quantity = qty_match.group(1)

        # Look for structured product description before quantity
        # Find the block of text between "supply of:" (or similar) and "Qty:"
        desc_match = re.search(
            r"(?:supply\s+of|requirement\s+for(?:\s+the\s+supply\s+of)?)\s*:?\s*\n*(.+?)(?=Qty\s*[:\-]?\s*\d+)",
            body,
            re.IGNORECASE | re.DOTALL,
        )

        if desc_match:
            raw_desc = desc_match.group(1).strip()
            # Clean up: join lines, remove excess whitespace
            desc_lines = [
                ln.strip() for ln in raw_desc.splitlines() if ln.strip()
            ]
            description = ", ".join(desc_lines)
            # Clean up double spaces and extra commas
            description = re.sub(r"\s+", " ", description)
            description = re.sub(r",\s*,", ",", description)

            items.append(
                RFQItem(index=1, description=description, quantity=quantity)
            )

        return items

    # ------------------------------------------------------------------
    # Attachment processing
    # ------------------------------------------------------------------

    def _process_attachments(
        self, msg, source_path: str
    ) -> Optional[RFQData]:
        """Save attachments and process PDF/XLSX ones."""
        if not msg.attachments:
            return None

        import shutil
        temp_dir = tempfile.mkdtemp(prefix="scso_rfq_")
        merged = RFQData()

        try:
            for att in msg.attachments:
                filename = att.longFilename or att.shortFilename
                if not filename:
                    continue

                # Skip images and other non-data attachments
                ext = os.path.splitext(filename)[1].lower()
                if ext not in (".pdf", ".xlsx", ".xls", ".docx", ".zip"):
                    continue

                att_path = os.path.join(temp_dir, filename)
                try:
                    att.save(customPath=temp_dir)

                    if ext == ".pdf":
                        from extractors.pdf_extractor import PDFExtractor
                        pdf_data = PDFExtractor().extract(att_path)
                        self._merge_data(merged, pdf_data)

                    elif ext in (".xlsx", ".xls"):
                        from extractors.xlsx_extractor import XLSXExtractor
                        xlsx_data = XLSXExtractor().extract(att_path)
                        self._merge_data(merged, xlsx_data)

                except Exception:
                    continue  # Skip problematic attachments
        finally:
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

        return merged if (merged.items or merged.raw_extracted_text) else None

    def _merge_data(self, target: RFQData, source: RFQData) -> None:
        """Merge source data into target (non-destructive)."""
        if source.items:
            target.items.extend(source.items)
        if source.tender_number and not target.tender_number:
            target.tender_number = source.tender_number
        if source.closing_date and not target.closing_date:
            target.closing_date = source.closing_date
        if source.raw_extracted_text:
            target.raw_extracted_text += "\n" + source.raw_extracted_text

    # ------------------------------------------------------------------
    # Section auto-detection
    # ------------------------------------------------------------------

    def _auto_detect_sections(self, data: RFQData, body: str) -> None:
        """Auto-detect which template sections to include."""
        body_lower = body.lower()

        data.include_coo_requirement_line = (
            "certificate of origin" in body_lower
            or "country of origin" in body_lower
        )
        data.include_coo_section = data.include_coo_requirement_line

        data.include_inspection_requirement_line = (
            "inspection" in body_lower
            or "third party" in body_lower
            or "3rd party" in body_lower
        )
        data.include_inspection_section = data.include_inspection_requirement_line

        data.include_general_note = (
            "hazardous" in body_lower
            or "intrinsically safe" in body_lower
        )
