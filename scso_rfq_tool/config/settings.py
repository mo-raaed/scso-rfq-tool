"""Persistent user settings for the SCSO RFQ Tool."""

import json
import os
from typing import Dict, Any, List

SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".scso_rfq_tool")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "engineer_names": [],           # List of stored engineer names
    "default_engineer_name": "",    # The default (first in dropdown)
    "last_output_folder": "",
    "default_delivery_terms": "Ex-Work, FOB, FCA.",
    "coo_requirement_text": "Certificate of Origin is required, as shown below.",
    "inspection_requirement_text": "3rd party inspection is required as shown below.",
    "inspection_section_text": (
        "3rd Party Inspection:\n"
        "The Third-Party inspection will be responsible to release the certificate of inspection, "
        "ITD inspection report as well as the release notes for this project.\n"
        "The list of inspection Companies that is approved by our clients as shown below:\n"
        "Bureau Veritas.\n"
        "Intertek Global\n\n"
        "Please be informed that the cost of the inspection and coordination will be handled by our company."
    ),
    "coo_section_text": (
        "Certificate of Origin (COO):\n"
        "Provide Certificate of origin legalized by Iraqi embassy at country of origin at time of order."
    ),
    "general_note_text": (
        "General Note:\n"
        "All electronic field instruments must be intrinsically safe IP 67 suitable to operation hazardous area class I, div 1, group C and D."
    ),
    "country_of_origin_text": (
        "Country of Origin:\n"
        "Accepted Country of Origin: {Italy - Germany - Spain}."
    ),
    "packing_text": "As per manufacturer standards.",
}


def load_settings() -> Dict[str, Any]:
    """Load settings from disk, merging with defaults."""
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            settings.update(saved)
        except (json.JSONDecodeError, OSError):
            pass  # Corrupt file → use defaults
    return settings


def save_settings(settings: Dict[str, Any]) -> None:
    """Persist settings to disk using atomic replacement to prevent corruption."""
    os.makedirs(SETTINGS_DIR, exist_ok=True)
    temp_file = SETTINGS_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        # Atomically rename to overwrite original file
        if os.path.exists(SETTINGS_FILE):
            os.remove(SETTINGS_FILE)
        os.rename(temp_file, SETTINGS_FILE)
    except Exception:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def add_engineer_name(settings: Dict[str, Any], name: str) -> None:
    """Add a name to the stored list (avoid duplicates, keep at front)."""
    name = name.strip()
    if not name:
        return
    names: List[str] = settings.get("engineer_names", [])
    if name in names:
        names.remove(name)
    names.insert(0, name)          # Most-recently-used first
    settings["engineer_names"] = names
    settings["default_engineer_name"] = names[0]


def get_template_path() -> str:
    """Return the path to the bundled SCSO RFQ template."""
    # When running from source
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_path = os.path.join(base, "resources", "SCSO RFQ.docx")
    if os.path.exists(source_path):
        return source_path

    # When packaged with PyInstaller (files next to .exe)
    import sys
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        frozen_path = os.path.join(exe_dir, "resources", "SCSO RFQ.docx")
        if os.path.exists(frozen_path):
            return frozen_path

    raise FileNotFoundError(
        "Could not find the SCSO RFQ template. "
        "Expected at: " + source_path
    )
