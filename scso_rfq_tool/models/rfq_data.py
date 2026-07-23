"""Data models for the SCSO RFQ Automation Tool."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RFQItem:
    """Represents a single line item in the RFQ."""
    index: int = 0
    description: str = ""
    quantity: str = ""
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    part_number: Optional[str] = None


@dataclass
class RFQData:
    """All data needed to populate the RFQ template."""

    # ----- Header fields (always present) -----
    ref_number: str = ""                        # Internal SCSO reference (e.g. "4783")
    tender_subject: str = ""                    # Short description
    closing_date: str = ""                      # Date string (various formats)

    # ----- Optional header fields -----
    end_user: str = ""
    end_user_address: str = ""
    tender_number: str = ""                     # External tender/RFQ number
    project_name: str = ""

    # ----- Line items -----
    items: List[RFQItem] = field(default_factory=list)

    # ----- Footer -----
    engineer_name: str = ""

    # ----- Tender Requirements toggles -----
    delivery_terms: str = "Ex-Work, FOB, FCA."
    include_coo_requirement_line: bool = True   # "Certificate of Origin is required…"
    include_inspection_requirement_line: bool = True  # "3rd party inspection is required…"
    include_end_user: bool = False
    include_end_user_address: bool = False
    include_tender_number: bool = False
    include_project_name: bool = False

    # ----- Packing section -----
    packing_header: str = "Packing Requirements"
    packing_text: str = "As per manufacturer standards."
    packing_detail: str = (
        "Please inform us of the estimated weight and Packing details "
        "to calculate the shipping cost for the end-user."
    )

    # ----- Optional body sections -----
    include_inspection_section: bool = True     # 3rd Party Inspection section
    include_coo_section: bool = True            # Certificate of Origin (COO) section
    include_general_note: bool = True           # General Note section
    include_country_of_origin: bool = False     # Country of Origin section

    # ----- Section texts (allows user-editable content in GUI) -----
    coo_requirement_text: str = "Certificate of Origin is required, as shown below."
    inspection_requirement_text: str = "3rd party inspection is required as shown below."
    
    inspection_section_text: str = (
        "3rd Party Inspection:\n"
        "The Third-Party inspection will be responsible to release the certificate of inspection, "
        "ITD inspection report as well as the release notes for this project.\n"
        "The list of inspection Companies that is approved by our clients as shown below:\n"
        "Bureau Veritas.\n"
        "Intertek Global\n\n"
        "Please be informed that the cost of the inspection and coordination will be handled by our company."
    )
    
    coo_section_text: str = (
        "Certificate of Origin (COO):\n"
        "Provide Certificate of origin legalized by Iraqi embassy at country of origin at time of order."
    )
    
    general_note_text: str = (
        "General Note:\n"
        "All electronic field instruments must be intrinsically safe IP 67 suitable to operation hazardous area class I, div 1, group C and D."
    )
    
    country_of_origin_text: str = (
        "Country of Origin:\n"
        "Accepted Country of Origin: {Italy - Germany - Spain}."
    )

    # ----- Custom notes (extra paragraphs before SCOPE of Supply) -----
    custom_notes: List[str] = field(default_factory=list)

    # ----- Output options -----
    generate_split_rfqs: bool = False
    output_folder: str = ""
    output_filename: str = ""                   # e.g. "Request #4783 Coriolis flowmeter"

    # ----- Source tracking -----
    source_file_path: str = ""
    raw_extracted_text: str = ""                # For debugging / user review
