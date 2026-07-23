"""PDF text extractor — handles text-based and scanned PDFs."""

import re
import os
from typing import List, Tuple, Optional

from models.rfq_data import RFQData, RFQItem
from extractors.base import BaseExtractor


class PDFExtractor(BaseExtractor):
    """Extracts RFQ data from PDF files.

    Strategy:
      1. Try pdfplumber text extraction first.
      2. If text is too short / empty → try OCR with pytesseract.
      3. If OCR is unavailable → return raw images flag for manual entry.
    """

    MIN_USEFUL_TEXT_LENGTH = 50  # chars — below this we assume scanned

    @staticmethod
    def can_handle(file_path: str) -> bool:
        return file_path.lower().endswith(".pdf")

    def extract(self, file_path: str) -> RFQData:
        data = RFQData(source_file_path=file_path)
        full_text = self._extract_text(file_path)

        if len(full_text.strip()) < self.MIN_USEFUL_TEXT_LENGTH or self._is_text_garbage(full_text):
            # Likely scanned — try OCR
            full_text = self._try_ocr(file_path)

        data.raw_extracted_text = full_text

        if full_text.strip():
            # Try to detect Arabic content and translate
            full_text = self._handle_translation(full_text)
            data.raw_extracted_text = full_text

            # Try structured Petronas-style parsing
            rfq_num, items = self._parse_petronas_format(full_text)
            if items:
                data.tender_number = rfq_num or ""
                data.items = items
                data.include_tender_number = bool(rfq_num)
                # Try to extract closing date
                data.closing_date = self._extract_date(full_text)
                # Auto-detect sections
                self._auto_detect_sections(data, full_text)
                return data

            # Try generic item extraction
            items = self._parse_generic_items(full_text)
            if items:
                data.items = items

            # Try to extract metadata fields
            data.closing_date = self._extract_date(full_text)
            data.tender_subject = self._extract_subject(full_text, file_path)
            self._auto_detect_sections(data, full_text)

        return data

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_text(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
            return "\n".join(pages)
        except Exception:
            return ""

    def _try_ocr(self, pdf_path: str) -> str:
        """Attempt OCR on a scanned PDF. Falls back gracefully."""
        try:
            import fitz  # PyMuPDF
            from PIL import Image
            import pytesseract
            import io

            doc = fitz.open(pdf_path)
            all_text = []

            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))

                # Try English + Arabic
                try:
                    text = pytesseract.image_to_string(img, lang="eng+ara")
                except Exception:
                    text = pytesseract.image_to_string(img, lang="eng")

                all_text.append(text)

            doc.close()
            return "\n".join(all_text)

        except ImportError:
            # pytesseract or PyMuPDF not available
            return "[OCR_UNAVAILABLE] This PDF appears to be scanned. "
        except Exception as e:
            return f"[OCR_ERROR] Could not OCR this PDF: {e}"

    # ------------------------------------------------------------------
    # Translation
    # ------------------------------------------------------------------

    def _has_arabic(self, text: str) -> bool:
        """Detect if text contains Arabic characters."""
        arabic_pattern = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+")
        matches = arabic_pattern.findall(text)
        # Only consider it Arabic if there's a substantial amount
        total_arabic = sum(len(m) for m in matches)
        return total_arabic > 20

    def _handle_translation(self, text: str) -> str:
        """If text contains Arabic, attempt translation."""
        if not self._has_arabic(text):
            return text

        try:
            from deep_translator import GoogleTranslator

            # Split into chunks (Google Translate limit ~5000 chars)
            chunks = self._split_text_chunks(text, 4500)
            translated_chunks = []

            translator = GoogleTranslator(source="ar", target="en")
            for chunk in chunks:
                try:
                    translated = translator.translate(chunk)
                    translated_chunks.append(translated or chunk)
                except Exception:
                    translated_chunks.append(chunk)

            translated_text = "\n".join(translated_chunks)
            # Return both original and translation for user review
            return (
                "=== TRANSLATED FROM ARABIC (please review) ===\n"
                + translated_text
                + "\n\n=== ORIGINAL ARABIC TEXT ===\n"
                + text
            )

        except ImportError:
            return (
                "[TRANSLATION_UNAVAILABLE] Arabic text detected but "
                "deep-translator is not installed.\n\n" + text
            )
        except Exception:
            return text

    def _split_text_chunks(self, text: str, max_len: int) -> List[str]:
        """Split text into chunks respecting line boundaries."""
        lines = text.splitlines(keepends=True)
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for line in lines:
            if current_len + len(line) > max_len and current:
                chunks.append("".join(current))
                current = []
                current_len = 0
            current.append(line)
            current_len += len(line)

        if current:
            chunks.append("".join(current))
        return chunks

    # ------------------------------------------------------------------
    # Petronas-style structured parsing (from reference script)
    # ------------------------------------------------------------------

    def _parse_petronas_format(
        self, text: str
    ) -> Tuple[Optional[str], List[RFQItem]]:
        """Parse the Petronas RFx Material Specification format."""
        # Extract RFQ Number
        rfq_match = re.search(
            r"RFQ\s+NUMBER\s*:\s*(\d+)", text, re.IGNORECASE
        )
        rfq_num = rfq_match.group(1) if rfq_match else None

        # Item pattern: Item_Num ProductNo Quantity Unit Description
        item_re = re.compile(
            r"^\s*(\d+)\s+(\d{8})\s+([\d,.]+)\s+([A-Z]{2})\s+(.+)$"
        )

        lines = text.splitlines()
        items_raw: List[dict] = []
        current_item: Optional[dict] = None

        for line in lines:
            stripped = line.strip()
            m = item_re.match(stripped)

            if m:
                if current_item:
                    items_raw.append(current_item)
                current_item = {
                    "index": int(m.group(1)),
                    "product_no": m.group(2),
                    "quantity_str": m.group(3),
                    "unit": m.group(4),
                    "raw_description": m.group(5),
                    "attributes": {},
                }
            elif current_item:
                attr_match = re.match(
                    r"^\s*([^:]+?)\s*:\s*(.+?)\s*$", stripped
                )
                if attr_match:
                    key = attr_match.group(1).strip()
                    val = attr_match.group(2).strip()
                    current_item["attributes"][key] = val

        if current_item:
            items_raw.append(current_item)

        if not items_raw:
            return rfq_num, []

        # Process into RFQItem objects
        processed: List[RFQItem] = []
        for it in items_raw:
            attrs = it["attributes"]

            # Quantity
            try:
                q = float(it["quantity_str"].replace(",", ""))
                qty_str = str(int(q)) if q == int(q) else str(q)
            except ValueError:
                qty_str = it["quantity_str"]

            # Manufacturer
            manufacturer = (
                attrs.get("MANUFACTURER NAME")
                or attrs.get("END ITEM MANUFACTURER NAME")
            )
            if manufacturer == "-":
                manufacturer = None

            # Model
            model = attrs.get("MODEL NUMBER") or attrs.get("MODEL")
            if model == "-":
                model = None

            # Part number
            part_no = attrs.get("MANUFACTURER PART NUMBER")
            if part_no == "-":
                part_no = None

            # Fallback manufacturer from description
            if not manufacturer:
                if model:
                    manufacturer = model.strip()
                else:
                    desc = it["raw_description"]
                    parts = [p.strip() for p in desc.split(",") if p.strip()]
                    if len(parts) >= 2:
                        manufacturer = f"{parts[0]} {parts[1]}"
                    else:
                        manufacturer = desc

            # Build description string
            desc_parts = [it["raw_description"]]
            if manufacturer:
                desc_parts.append(f"({manufacturer})")
            extra = []
            if part_no:
                extra.append(f"PN: {part_no}")
            if model:
                extra.append(f"Model: {model}")
            desc_str = " ".join(desc_parts)
            if extra:
                desc_str += f", {', '.join(extra)}"

            processed.append(
                RFQItem(
                    index=it["index"],
                    description=desc_str,
                    quantity=qty_str,
                    manufacturer=manufacturer,
                    model=model,
                    part_number=part_no,
                )
            )

        return rfq_num, processed

    # ------------------------------------------------------------------
    # Generic item parsing (best-effort for other PDF formats)
    # ------------------------------------------------------------------

    def _parse_generic_items(self, text: str) -> List[RFQItem]:
        """Try to find item-like patterns in generic PDFs."""
        items: List[RFQItem] = []

        # Pattern: look for numbered lists with quantities
        # e.g. "1. Description text ... Qty: 5"
        numbered = re.findall(
            r"(\d+)\.\s+(.+?)(?:Qty|QTY|Quantity|qty)\s*[:\-]?\s*(\d+)",
            text,
            re.IGNORECASE,
        )
        for idx, desc, qty in numbered:
            items.append(
                RFQItem(index=int(idx), description=desc.strip(), quantity=qty)
            )

        if items:
            return items

        # Pattern: look for tag numbers (like Majnoon CP2-506FT-001)
        # First try INDEX page format: "5 CP2-506FT -001 5"
        index_tags = re.findall(
            r"^\s*\d+\s+(CP\d+-\d+[A-Z]{2}\s*-\s*\d+)\s+\d+\s*$",
            text,
            re.MULTILINE,
        )
        # Fallback: find all tag patterns and deduplicate
        if not index_tags:
            index_tags = re.findall(r"(CP\d+-\d+[A-Z]{2}\s*-\s*\d+)", text)

        # Deduplicate while preserving order
        seen_tags = set()
        unique_tags = []
        for tag in index_tags:
            normalized = re.sub(r"\s+", "", tag)
            if normalized not in seen_tags:
                seen_tags.add(normalized)
                unique_tags.append(tag.strip())

        if unique_tags:
            for i, tag in enumerate(unique_tags, 1):
                items.append(
                    RFQItem(
                        index=i,
                        description=f"{tag}\nAccording to the attached data sheet",
                        quantity="1",
                    )
                )
            return items

        return []

    # ------------------------------------------------------------------
    # Metadata extraction helpers
    # ------------------------------------------------------------------

    def _extract_date(self, text: str) -> str:
        """Try to find a closing date in the text."""
        patterns = [
            r"(?:closing|deadline|due)\s*(?:date)?\s*[:\-]\s*([^\n]+)",
            r"(?:before|by|no\s+later\s+than)\s+(\d{1,2}[\s/\-\.]+\w+[\s/\-\.]+\d{4})",
            r"Delivery\s+Date\s*:\s*(\d{2}\.\d{2}\.\d{4})",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    def _extract_subject(self, text: str, file_path: str) -> str:
        """Try to determine the tender subject."""
        # Try to get from tender title
        m = re.search(r"Tender\s+Title\s*:\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:100]

        # Try document title/tide (e.g. Document Tide : DATASHEETS FOR CORIOLIS FLOWMETER)
        m = re.search(
            r"Document\s+Ti[dt]e\s*:\s*([^\n]+)",
            text,
            re.IGNORECASE,
        )
        if m:
            title = m.group(1).strip()
            # Split by common metadata headers in the title block
            title = re.split(r"\s+(?:Comp|Job|Rev|Page|Date)\b", title, flags=re.IGNORECASE)[0].strip()
            title = re.sub(r"^[^\w]+|[^\w]+$", "", title).strip()
            if len(title) > 5:
                return title.title()[:100]

        # Try document title block "DOCUMENT TITLE:"
        m = re.search(
            r"DOCUMENT\s+TITLE\s*:\s*\n?\s*([^\n]+)",
            text,
            re.IGNORECASE,
        )
        if m:
            title = m.group(1).strip()
            # Clean up: remove revision/date/approval info
            title = re.sub(
                r"\s*(Rev\.?\s*\d+|Comp[a-z]*|Date|Page|Approved|For).*$",
                "",
                title,
                flags=re.IGNORECASE,
            ).strip()
            if len(title) > 5:
                return title.title()[:100]

        # Fallback to filename (cleaned up)
        base = os.path.splitext(os.path.basename(file_path))[0]
        # Remove common prefixes like "RFx -"
        base = re.sub(r"^RFx\s*-\s*", "", base)
        return base[:80]

    def _auto_detect_sections(self, data: RFQData, text: str) -> None:
        """Auto-detect which template sections should be included."""
        text_lower = text.lower()

        # Certificate of Origin — include if mentioned
        data.include_coo_requirement_line = (
            "certificate of origin" in text_lower
            or "country of origin" in text_lower
        )
        data.include_coo_section = data.include_coo_requirement_line

        # 3rd Party Inspection — include if mentioned
        data.include_inspection_requirement_line = (
            "inspection" in text_lower
            or "third party" in text_lower
            or "3rd party" in text_lower
        )
        data.include_inspection_section = data.include_inspection_requirement_line

        # General Note — include if hazardous area or intrinsically safe mentioned
        data.include_general_note = (
            "hazardous" in text_lower
            or "intrinsically safe" in text_lower
            or "ip 67" in text_lower
            or "ip67" in text_lower
        )

    def _is_text_garbage(self, text: str) -> bool:
        """Check if the text contains mostly garbled symbols instead of words."""
        if not text.strip():
            return True
        alnum_count = sum(1 for c in text if c.isalnum() or c.isspace())
        ratio = alnum_count / len(text)
        return ratio < 0.45
