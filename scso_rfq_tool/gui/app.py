"""SCSO RFQ Tool — Main GUI Application."""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.rfq_data import RFQData, RFQItem
from config.settings import (
    load_settings,
    save_settings,
    add_engineer_name,
    get_template_path,
)


# ======================================================================
# Constants
# ======================================================================

APP_TITLE = "SCSO RFQ Tool"
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 720
FILE_TYPES = [
    ("All supported", "*.msg;*.pdf;*.xlsx;*.xls;*.docx"),
    ("Outlook emails", "*.msg"),
    ("PDF files", "*.pdf"),
    ("Excel files", "*.xlsx;*.xls"),
    ("Word files", "*.docx"),
]
DELIVERY_TERM_OPTIONS = [
    "Ex-Work, FOB, FCA.",
    "Ex-Work.",
]


# ======================================================================
# Helper: Scrollable Frame
# ======================================================================

class ScrollableFrame(ttk.Frame):
    """A scrollable container frame using Canvas."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind(
            "<Configure>",
            lambda _: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        # Resize inner frame width with canvas
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(
                self.canvas_window, width=e.width
            ),
        )

        # Mouse wheel hover-only scrolling to prevent global scrolling errors
        self.canvas.bind("<Enter>", lambda _: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda _: self.canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event):
        # Only scroll if content is taller than the canvas height
        canvas_height = self.canvas.winfo_height()
        content_height = self.inner.winfo_height()
        if content_height <= canvas_height:
            return
            
        # Perform vertical scroll
        scroll_units = -1 * int(event.delta / 120)
        self.canvas.yview_scroll(scroll_units, "units")


# ======================================================================
# Item Edit Dialog
# ======================================================================

class ItemDialog(tk.Toplevel):
    """Pop-up dialog to add or edit an RFQ item."""

    def __init__(self, parent, item: RFQItem = None, title="Add Item"):
        super().__init__(parent)
        self.title(title)
        self.geometry("550x350")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()

        pad = {"padx": 10, "pady": 5}

        # Description
        ttk.Label(self, text="Description:").grid(
            row=0, column=0, sticky="nw", **pad
        )
        self.desc_text = scrolledtext.ScrolledText(
            self, width=50, height=8, wrap="word"
        )
        self.desc_text.grid(row=0, column=1, **pad)

        # Quantity
        ttk.Label(self, text="Quantity:").grid(
            row=1, column=0, sticky="w", **pad
        )
        self.qty_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.qty_var, width=20).grid(
            row=1, column=1, sticky="w", **pad
        )

        # Manufacturer (optional)
        ttk.Label(self, text="Manufacturer:").grid(
            row=2, column=0, sticky="w", **pad
        )
        self.mfg_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.mfg_var, width=40).grid(
            row=2, column=1, sticky="w", **pad
        )

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="OK", command=self._ok).pack(
            side="left", padx=10
        )
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side="left", padx=10
        )

        # Pre-fill if editing
        if item:
            self.desc_text.insert("1.0", item.description)
            self.qty_var.set(item.quantity)
            self.mfg_var.set(item.manufacturer or "")

        self.wait_window()

    def _ok(self):
        desc = self.desc_text.get("1.0", "end-1c").strip()
        qty = self.qty_var.get().strip()
        if not desc:
            messagebox.showwarning("Missing", "Description is required.", parent=self)
            return
        self.result = RFQItem(
            description=desc,
            quantity=qty or "1",
            manufacturer=self.mfg_var.get().strip() or None,
        )
        self.destroy()


# ======================================================================
# Translation Approval Dialog
# ======================================================================

class TranslationApprovalDialog(tk.Toplevel):
    """Dialog to review, edit, and approve automatic translations of Arabic inquiries."""

    def __init__(self, parent, arabic_text: str, english_translation: str):
        super().__init__(parent)
        self.title("Review Arabic → English Translation")
        self.geometry("800x550")
        self.transient(parent)
        self.grab_set()
        self.approved_text = None

        pad = {"padx": 10, "pady": 10}

        # Prompt
        ttk.Label(
            self,
            text="Arabic text was detected. Please review and edit the translation below:",
            font=("Segoe UI", 11, "bold"),
        ).pack(fill="x", **pad)

        # Main frame containing split view
        split_frame = ttk.Frame(self)
        split_frame.pack(fill="both", expand=True, padx=10)

        # Left panel: Original Arabic
        left_panel = ttk.LabelFrame(split_frame, text="Original Arabic Text", padding=5)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.arabic_box = scrolledtext.ScrolledText(left_panel, wrap="word")
        self.arabic_box.insert("1.0", arabic_text)
        self.arabic_box.config(state="disabled")  # Read-only
        self.arabic_box.pack(fill="both", expand=True)

        # Right panel: Editable English Translation
        right_panel = ttk.LabelFrame(split_frame, text="English Translation (Editable)", padding=5)
        right_panel.pack(side="right", fill="both", expand=True, padx=(5, 0))
        self.english_box = scrolledtext.ScrolledText(right_panel, wrap="word")
        self.english_box.insert("1.0", english_translation)
        self.english_box.pack(fill="both", expand=True)

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=15)
        
        ttk.Button(btn_frame, text="Approve & Proceed", command=self._approve, style="Accent.TButton").pack(side="right", padx=15)
        ttk.Button(btn_frame, text="Cancel & Use Raw Text", command=self.destroy).pack(side="right", padx=10)

        self.wait_window()

    def _approve(self):
        self.approved_text = self.english_box.get("1.0", "end-1c").strip()
        self.destroy()


# ======================================================================
# Settings Dialog
# ======================================================================

class SettingsDialog(tk.Toplevel):
    """Configuration menu to customize system defaults and template texts."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Global Settings & Template Defaults")
        self.geometry("750x650")
        self.transient(parent)
        self.grab_set()

        from config.settings import load_settings, save_settings
        self.settings = load_settings()

        # 1. Save / Cancel Buttons at the bottom (packed first so they stay visible)
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side="bottom", fill="x", pady=10)
        ttk.Button(btn_frame, text="Save Settings", command=self._save, style="Accent.TButton").pack(side="right", padx=15)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right", padx=10)

        # 2. Scrollable Frame fills the rest of the window
        scroll = ScrollableFrame(self)
        scroll.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        self.inner = scroll.inner

        pad = {"padx": 10, "pady": 5}

        # 3. Engineer names list
        ttk.Label(self.inner, text="Engineer Names (One per line):", font=("Segoe UI", 10, "bold")).pack(anchor="w", **pad)
        self.names_text = scrolledtext.ScrolledText(self.inner, height=4, width=60)
        self.names_text.pack(fill="x", **pad)
        names = self.settings.get("engineer_names", [])
        self.names_text.insert("1.0", "\n".join(names))

        # 2. Default delivery terms
        ttk.Label(self.inner, text="Default Delivery Terms:", font=("Segoe UI", 10, "bold")).pack(anchor="w", **pad)
        self.delivery_var = tk.StringVar(value=self.settings.get("default_delivery_terms", "Ex-Work, FOB, FCA."))
        combo = ttk.Combobox(self.inner, textvariable=self.delivery_var, values=["Ex-Work, FOB, FCA.", "Ex-Work."], width=30)
        combo.pack(anchor="w", **pad)

        # 3. Default Section Texts
        ttk.Label(self.inner, text="Default Texts for Template Sections:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(15, 5))

        self.text_boxes = {}
        sections = [
            ("coo_requirement_text", "Certificate of Origin Header Requirement Line:", 2),
            ("inspection_requirement_text", "3rd Party Inspection Header Requirement Line:", 2),
            ("inspection_section_text", "3rd Party Inspection Section:", 5),
            ("coo_section_text", "Certificate of Origin (COO) Section:", 3),
            ("general_note_text", "General Note Section:", 3),
            ("country_of_origin_text", "Country of Origin Section (Italy - Germany - Spain):", 3),
            ("packing_text", "Default Packing Text:", 2),
        ]

        for key, title, height in sections:
            ttk.Label(self.inner, text=title, font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)
            box = scrolledtext.ScrolledText(self.inner, height=height, width=70, wrap="word")
            box.pack(fill="x", **pad)
            
            # Load from settings
            val = self.settings.get(key, "")
            box.insert("1.0", val)
            self.text_boxes[key] = box

    def _save(self):
        # Update settings dictionary
        raw_names = self.names_text.get("1.0", "end-1c").strip()
        names = [n.strip() for n in raw_names.splitlines() if n.strip()]
        self.settings["engineer_names"] = names
        if names:
            self.settings["default_engineer_name"] = names[0]
        else:
            self.settings["default_engineer_name"] = ""

        self.settings["default_delivery_terms"] = self.delivery_var.get().strip()

        for key, box in self.text_boxes.items():
            self.settings[key] = box.get("1.0", "end-1c").strip()

        # Save settings
        save_settings(self.settings)
        messagebox.showinfo("Success", "Settings saved successfully!", parent=self)
        self.destroy()



# ======================================================================
# Main Application
# ======================================================================

class RFQApp:
    """Main application with a 3-screen wizard flow."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(800, 600)

        # State
        self.settings = load_settings()
        self.rfq_data: RFQData = RFQData()
        self.current_screen = None

        # Apply custom visual identity
        self._apply_visual_theme()

        # Screen container
        self.container = ttk.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.screens = {}
        self._build_file_screen()
        self._build_review_screen()
        self._build_progress_screen()

        self._show("file")

    def _apply_visual_theme(self) -> None:
        """Apply a highly cohesive, professional visual design system inspired by industrial engineering."""
        style = ttk.Style()
        style.theme_use("clam")

        # Visual Design Tokens
        BG_SLATE_DARK = "#1E2022"   # Deep slate charcoal
        BG_SLATE_LIGHT = "#F4F6F9"  # Soft slate canvas background
        ACCENT_STEEL = "#3D5A80"    # Steel blue for standard actions
        ACCENT_COPPER = "#E07A5F"   # Accent copper for primary actions
        CARD_WHITE = "#FFFFFF"      # Crisp white card background
        TEXT_DARK = "#2D3748"       # Deep text color
        BORDER_GRAY = "#D2D6DC"     # Clean soft outlines

        self.root.configure(bg=BG_SLATE_LIGHT)

        # Global Base Settings
        style.configure(".", background=BG_SLATE_LIGHT, foreground=TEXT_DARK, font=("Segoe UI", 10))

        # Frames & LabelFrames
        style.configure("TFrame", background=BG_SLATE_LIGHT)
        style.configure("TLabelframe", background=BG_SLATE_LIGHT, bordercolor=BORDER_GRAY, borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=BG_SLATE_LIGHT, foreground=ACCENT_STEEL, font=("Segoe UI Semibold", 10))

        # Specialized frames
        style.configure("Header.TFrame", background=BG_SLATE_DARK)
        style.configure("Card.TFrame", background=CARD_WHITE, bordercolor=BORDER_GRAY, borderwidth=1, relief="solid")
        style.configure("DropZone.TFrame", background="#F8FAFC", bordercolor="#CBD5E1", borderwidth=1, relief="solid")

        # Labels
        style.configure("TLabel", background=BG_SLATE_LIGHT, foreground=TEXT_DARK)
        style.configure("Header.TLabel", background=BG_SLATE_DARK, foreground=CARD_WHITE, font=("Segoe UI Semibold", 12))
        style.configure("Title.TLabel", background=BG_SLATE_LIGHT, foreground=BG_SLATE_DARK, font=("Segoe UI Semibold", 20))
        style.configure("Subtitle.TLabel", background=BG_SLATE_LIGHT, foreground="#5A6A85", font=("Segoe UI", 10))

        # Inputs
        style.configure("TEntry", fieldbackground=CARD_WHITE, bordercolor=BORDER_GRAY, borderwidth=1, relief="solid", padding=5)
        style.configure("TCombobox", fieldbackground=CARD_WHITE, background=BG_SLATE_LIGHT, arrowcolor=TEXT_DARK, bordercolor=BORDER_GRAY, borderwidth=1, relief="solid")
        style.map("TCombobox", fieldbackground=[("readonly", CARD_WHITE)], background=[("readonly", BG_SLATE_LIGHT)])

        # Checkbuttons
        style.configure("TCheckbutton", background=BG_SLATE_LIGHT, foreground=TEXT_DARK)
        style.map("TCheckbutton", background=[("active", BG_SLATE_LIGHT)])

        # Buttons
        # 1. Primary Action (Copper/Amber)
        style.configure("Accent.TButton", background=ACCENT_COPPER, foreground=CARD_WHITE, borderwidth=0, padding=(15, 8), font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton",
                  background=[("active", "#C86047"), ("disabled", "#F2D0C6")],
                  foreground=[("disabled", "#A0A0A0")])

        # 2. Secondary Action (Steel Blue)
        style.configure("Steel.TButton", background=ACCENT_STEEL, foreground=CARD_WHITE, borderwidth=0, padding=(10, 5), font=("Segoe UI Semibold", 9))
        style.map("Steel.TButton",
                  background=[("active", "#2C4360"), ("disabled", "#D1DDEB")],
                  foreground=[("disabled", "#A0A0A0")])

        # 3. Standard Outline Button (White/Light gray)
        style.configure("TButton", background=CARD_WHITE, foreground=TEXT_DARK, borderwidth=1, bordercolor=BORDER_GRAY, relief="solid", padding=5, font=("Segoe UI", 9))
        style.map("TButton",
                  background=[("active", "#ECEFF1"), ("disabled", "#F5F5F5")])

        # Treeview (Items table)
        style.configure("Treeview", background=CARD_WHITE, fieldbackground=CARD_WHITE, foreground=TEXT_DARK, rowheight=24, borderwidth=1, bordercolor=BORDER_GRAY, relief="solid", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=ACCENT_STEEL, foreground=CARD_WHITE, font=("Segoe UI Semibold", 9), relief="flat", padding=5)
        style.map("Treeview.Heading", background=[("active", "#2C4360")])

    # ------------------------------------------------------------------
    # Screen management
    # ------------------------------------------------------------------

    def _show(self, name: str) -> None:
        for frame in self.screens.values():
            frame.pack_forget()
        self.screens[name].pack(fill="both", expand=True)
        self.current_screen = name

    # ==================================================================
    # SCREEN 1: File Selection
    # ==================================================================

    def _build_file_screen(self) -> None:
        frame = ttk.Frame(self.container)
        self.screens["file"] = frame

        # Top Header Banner (Industrial Dark)
        banner = ttk.Frame(frame, style="Header.TFrame")
        banner.pack(fill="x", side="top")
        
        logo = ttk.Label(banner, text="✦ SCSO RFQ AUTOMATION TOOL", style="Header.TLabel")
        logo.pack(side="left", padx=20, pady=15)
        
        settings_btn = ttk.Button(
            banner, text="⚙ Settings", command=self._open_settings
        )
        settings_btn.pack(side="right", padx=20, pady=10)

        # Center Container (Content area)
        center_frame = ttk.Frame(frame, padding=35)
        center_frame.pack(fill="both", expand=True)

        # Main Workspace Card
        card = ttk.Frame(center_frame, style="Card.TFrame", padding=30)
        card.pack(fill="both", expand=True, padx=40, pady=10)

        # Large Visual Upload Zone
        zone = ttk.Frame(card, style="DropZone.TFrame", padding=25)
        zone.pack(fill="both", expand=True, pady=(0, 20))
        
        icon = tk.Label(zone, text="📄", font=("Segoe UI", 48), fg="#E07A5F", bg="#F8FAFC")
        icon.pack(pady=(15, 5))
        
        prompt = tk.Label(zone, text="Select inquiry file to start processing", font=("Segoe UI Semibold", 12), fg="#2D3748", bg="#F8FAFC")
        prompt.pack()
        
        hint = tk.Label(zone, text="Supported Formats: Outlook Emails (.msg), Inquiry PDFs (.pdf), Excel Sheets (.xlsx), Word Docs (.docx)", font=("Segoe UI", 9), fg="#7F8C8D", bg="#F8FAFC")
        hint.pack(pady=(5, 15))

        # Browse Path & File Input Row
        file_row = tk.Frame(zone, bg="#F8FAFC")
        file_row.pack(fill="x", padx=40, pady=10)
        
        self.file_path_var = tk.StringVar()
        entry = ttk.Entry(file_row, textvariable=self.file_path_var, width=50, style="TEntry")
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(file_row, text="Browse File...", command=self._browse_file)
        browse_btn.pack(side="right")

        # CTA Button
        self.extract_btn = ttk.Button(
            card,
            text="Extract Data & Review →",
            command=self._on_extract,
            style="Accent.TButton",
        )
        self.extract_btn.pack(pady=(10, 5))

        # Status Label
        self.file_status_var = tk.StringVar(value="Ready")
        status_lbl = ttk.Label(
            card,
            textvariable=self.file_status_var,
            font=("Segoe UI Semibold", 9),
            foreground="#5A6A85",
            background="#FFFFFF",
        )
        status_lbl.pack()

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Inquiry File",
            filetypes=FILE_TYPES,
        )
        if path:
            self.file_path_var.set(path)

    def _on_extract(self) -> None:
        file_path = self.file_path_var.get().strip()
        if not file_path or not os.path.isfile(file_path):
            messagebox.showwarning("No File", "Please select a valid file.")
            return

        self.file_status_var.set("Extracting data… please wait.")
        self.extract_btn.config(state="disabled")
        self.root.update_idletasks()

        # Run extraction in background thread
        threading.Thread(
            target=self._extract_thread, args=(file_path,), daemon=True
        ).start()

    def _extract_thread(self, file_path: str) -> None:
        """Run extraction in a background thread."""
        try:
            data = self._run_extractor(file_path)
            self.root.after(0, self._extraction_done, data)
        except Exception as e:
            self.root.after(0, self._extraction_error, str(e))

    def _run_extractor(self, file_path: str) -> RFQData:
        """Select the correct extractor, run it, and search for companion files to merge data."""
        ext = os.path.splitext(file_path)[1].lower()

        # Step 1: Run the primary extractor
        if ext == ".msg":
            from extractors.msg_extractor import MSGExtractor
            data = MSGExtractor().extract(file_path)
        elif ext == ".pdf":
            from extractors.pdf_extractor import PDFExtractor
            data = PDFExtractor().extract(file_path)
        elif ext in (".xlsx", ".xls"):
            from extractors.xlsx_extractor import XLSXExtractor
            data = XLSXExtractor().extract(file_path)
        elif ext == ".docx":
            from extractors.docx_extractor import DOCXExtractor
            data = DOCXExtractor().extract(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        # Step 2: Look for companion files to merge metadata and items
        self._merge_companion_files(data, file_path)

        return data

    def _merge_companion_files(self, data: RFQData, file_path: str) -> None:
        """Find companion files (like sibling MSG or PDF files) and merge their data."""
        import glob
        source_dir = os.path.dirname(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        # Go up to look for sibling project directories
        project_dir = source_dir
        for _ in range(3):
            # Check if this dir has 'Inquiry' or 'Quotation - Customer' folders
            inquiry_dir = os.path.join(project_dir, "Inquiry")
            quote_dir = os.path.join(project_dir, "Quotation - Customer")
            if os.path.isdir(inquiry_dir) or os.path.isdir(quote_dir):
                break
            project_dir = os.path.dirname(project_dir)

        inquiry_dir = os.path.join(project_dir, "Inquiry")
        correspondence_dir = os.path.join(project_dir, "Quotation - Customer", "Correspondence")

        if ext == ".pdf":
            # Search for companion MSG files
            if os.path.isdir(correspondence_dir):
                msg_files = glob.glob(os.path.join(correspondence_dir, "*.msg"))
                if msg_files:
                    # Parse the first found MSG file to merge email metadata
                    from extractors.msg_extractor import MSGExtractor
                    msg_data = MSGExtractor().extract(msg_files[0])
                    self._merge_rfq_data(data, msg_data)

        elif ext == ".msg":
            # Search for companion PDF or XLSX files
            if os.path.isdir(inquiry_dir):
                doc_files = glob.glob(os.path.join(inquiry_dir, "*.pdf")) + \
                            glob.glob(os.path.join(inquiry_dir, "*.xlsx")) + \
                            glob.glob(os.path.join(inquiry_dir, "*.xls"))
                if doc_files:
                    # Find first valid document to extract items
                    doc_path = doc_files[0]
                    doc_ext = os.path.splitext(doc_path)[1].lower()
                    if doc_ext == ".pdf":
                        from extractors.pdf_extractor import PDFExtractor
                        doc_data = PDFExtractor().extract(doc_path)
                    else:
                        from extractors.xlsx_extractor import XLSXExtractor
                        doc_data = XLSXExtractor().extract(doc_path)
                    
                    self._merge_rfq_data(data, doc_data)

    def _merge_rfq_data(self, target: RFQData, source: RFQData) -> None:
        """Merge source RFQData fields into target if target has them empty."""
        if not target.tender_subject and source.tender_subject:
            target.tender_subject = source.tender_subject
        if not target.closing_date and source.closing_date:
            target.closing_date = source.closing_date
        if not target.tender_number and source.tender_number:
            target.tender_number = source.tender_number
            target.include_tender_number = True
        if not target.end_user and source.end_user:
            target.end_user = source.end_user
            target.include_end_user = True
        if not target.items and source.items:
            target.items = source.items
        if source.raw_extracted_text:
            target.raw_extracted_text += "\n\n=== COMPANION DATA ===\n" + source.raw_extracted_text

    def _extraction_done(self, data: RFQData) -> None:
        """Handle successful extraction — populate review screen."""
        self.rfq_data = data
        self.file_status_var.set(
            f"Extracted {len(data.items)} item(s). Review below."
        )
        self.extract_btn.config(state="normal")

        # Check for automatic translation and prompt for approval
        if "=== TRANSLATED FROM ARABIC" in data.raw_extracted_text:
            parts = data.raw_extracted_text.split("=== ORIGINAL ARABIC TEXT ===")
            arabic = parts[1].strip() if len(parts) > 1 else ""
            
            eng_parts = parts[0].split("=== TRANSLATED FROM ARABIC (please review) ===")
            english = eng_parts[1].strip() if len(eng_parts) > 1 else parts[0].strip()
            
            # Clean up warning prefix if present
            english = english.replace("[TRANSLATION_UNAVAILABLE] Arabic text detected but deep-translator is not installed.", "").strip()

            dlg = TranslationApprovalDialog(self.root, arabic, english)
            if dlg.approved_text:
                # Update text to the approved version
                data.raw_extracted_text = dlg.approved_text
                
                # Re-parse items, closing date, subject from approved English text
                from extractors.pdf_extractor import PDFExtractor
                pdf_ext = PDFExtractor()
                items = pdf_ext._parse_generic_items(dlg.approved_text)
                if items:
                    data.items = items
                    self.file_status_var.set(f"Extracted {len(items)} item(s) from approved translation.")
                
                date = pdf_ext._extract_date(dlg.approved_text)
                if date:
                    data.closing_date = date
                    
                subject = pdf_ext._extract_subject(dlg.approved_text, data.source_file_path)
                if subject and subject != os.path.splitext(os.path.basename(data.source_file_path))[0]:
                    data.tender_subject = subject

        # Auto-detect output folder: look for /RFQ sibling to /Inquiry
        source_dir = os.path.dirname(data.source_file_path)
        # If source is in /Inquiry or /Correspondence, go up to project root
        parent = source_dir
        for _ in range(3):
            rfq_folder = os.path.join(parent, "RFQ")
            if os.path.isdir(rfq_folder) or os.path.isdir(
                os.path.join(parent, "Inquiry")
            ):
                rfq_folder = os.path.join(parent, "RFQ")
                os.makedirs(rfq_folder, exist_ok=True)
                data.output_folder = rfq_folder
                break
            parent = os.path.dirname(parent)

        if not data.output_folder:
            data.output_folder = source_dir

        # Set defaults
        data.engineer_name = self.settings.get("default_engineer_name", "")

        # Auto-generate filename
        if data.ref_number and data.tender_subject:
            data.output_filename = (
                f"Request #{data.ref_number} {data.tender_subject}"
            )

        self._populate_review_screen()
        self._show("review")

    def _extraction_error(self, error_msg: str) -> None:
        self.file_status_var.set(f"Error: {error_msg}")
        self.extract_btn.config(state="normal")
        messagebox.showerror("Extraction Error", error_msg)

    # ==================================================================
    # SCREEN 2: Review & Edit
    # ==================================================================

    def _build_review_screen(self) -> None:
        frame = ttk.Frame(self.container)
        self.screens["review"] = frame

        # Top Header Banner (Industrial Dark)
        top = ttk.Frame(frame, style="Header.TFrame")
        top.pack(fill="x", side="top")
        
        back_btn = ttk.Button(top, text="← Back", command=lambda: self._show("file"))
        back_btn.pack(side="left", padx=20, pady=10)
        
        title_lbl = ttk.Label(
            top, text="Review & Edit RFQ Data", style="Header.TLabel"
        )
        title_lbl.pack(side="left", padx=10, pady=15)
        
        self.generate_btn = ttk.Button(
            top, text="Generate RFQ Documents →", command=self._on_generate, style="Accent.TButton"
        )
        self.generate_btn.pack(side="right", padx=20, pady=10)

        # Settings button on top bar
        settings_btn = ttk.Button(
            top, text="⚙ Settings", command=self._open_settings
        )
        settings_btn.pack(side="right", padx=10, pady=10)

        # Scrollable content
        self.scroll_frame = ScrollableFrame(frame)
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.inner = self.scroll_frame.inner

        # Build all sections (widgets stored as attributes)
        self._build_header_section()
        self._build_items_section()
        self._build_options_section()
        self._build_output_section()

    def _build_header_section(self) -> None:
        """Build the RFQ header fields section."""
        sec = ttk.LabelFrame(self.inner, text="RFQ Header", padding=10)
        sec.pack(fill="x", padx=10, pady=5)

        self.header_vars = {}
        fields = [
            ("ref_number", "Ref. #:", 20),
            ("tender_subject", "Tender Subject:", 60),
        ]
        for row_i, (key, label, width) in enumerate(fields):
            ttk.Label(sec, text=label).grid(
                row=row_i, column=0, sticky="w", padx=5, pady=3
            )
            var = tk.StringVar()
            ttk.Entry(sec, textvariable=var, width=width).grid(
                row=row_i, column=1, sticky="w", padx=5, pady=3
            )
            self.header_vars[key] = var

        # Closing Date calendar selection (DateEntry)
        row_i = len(fields)
        ttk.Label(sec, text="Closing Date:").grid(
            row=row_i, column=0, sticky="w", padx=5, pady=3
        )
        from tkcalendar import DateEntry
        self.closing_date_entry = DateEntry(
            sec, width=22, background='#3D5A80', foreground='white', borderwidth=1,
            date_pattern='dd.mm.yyyy', relief="solid"
        )
        self.closing_date_entry.grid(row=row_i, column=1, sticky="w", padx=5, pady=3)

        # Optional fields with checkboxes
        self.optional_vars = {}
        opt_fields = [
            ("end_user", "End-User:", "include_end_user", 50),
            ("end_user_address", "End-User Address:", "include_end_user_address", 50),
            ("tender_number", "Tender Number:", "include_tender_number", 30),
            ("project_name", "Project Name:", "include_project_name", 50),
        ]
        for row_i, (key, label, toggle_key, width) in enumerate(
            opt_fields, start=len(fields) + 1
        ):
            check_var = tk.BooleanVar()
            chk = ttk.Checkbutton(sec, text=label, variable=check_var)
            chk.grid(row=row_i, column=0, sticky="w", padx=5, pady=3)

            val_var = tk.StringVar()
            ttk.Entry(sec, textvariable=val_var, width=width).grid(
                row=row_i, column=1, sticky="w", padx=5, pady=3
            )

            self.optional_vars[key] = (check_var, val_var, toggle_key)

    def _build_items_section(self) -> None:
        """Build the items table section."""
        sec = ttk.LabelFrame(self.inner, text="Scope of Supply — Items", padding=10)
        sec.pack(fill="x", padx=10, pady=5)

        # Treeview table
        cols = ("item", "description", "qty")
        self.items_tree = ttk.Treeview(
            sec, columns=cols, show="headings", height=8
        )
        self.items_tree.heading("item", text="#")
        self.items_tree.heading("description", text="Description")
        self.items_tree.heading("qty", text="QTY")
        self.items_tree.column("item", width=40, stretch=False)
        self.items_tree.column("description", width=550)
        self.items_tree.column("qty", width=60, stretch=False)

        tree_scroll = ttk.Scrollbar(
            sec, orient="vertical", command=self.items_tree.yview
        )
        self.items_tree.configure(yscrollcommand=tree_scroll.set)

        self.items_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="left", fill="y")

        # Buttons
        btn_frame = ttk.Frame(sec)
        btn_frame.pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Add Item", command=self._add_item, style="Steel.TButton").pack(
            fill="x", pady=3
        )
        ttk.Button(btn_frame, text="Edit Item", command=self._edit_item, style="Steel.TButton").pack(
            fill="x", pady=3
        )
        ttk.Button(btn_frame, text="Remove Item", command=self._remove_item, style="Steel.TButton").pack(
            fill="x", pady=3
        )
        ttk.Button(
            btn_frame, text="Move Up ↑", command=lambda: self._move_item(-1), style="Steel.TButton"
        ).pack(fill="x", pady=3)
        ttk.Button(
            btn_frame, text="Move Down ↓", command=lambda: self._move_item(1), style="Steel.TButton"
        ).pack(fill="x", pady=3)

    def _build_options_section(self) -> None:
        """Build the template options section with toggleable detail text boxes."""
        sec = ttk.LabelFrame(self.inner, text="Template Options & Editable Sections", padding=10)
        sec.pack(fill="x", padx=10, pady=5)

        # Delivery terms
        ttk.Label(sec, text="Delivery Terms:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5
        )
        self.delivery_var = tk.StringVar()
        combo = ttk.Combobox(
            sec,
            textvariable=self.delivery_var,
            values=DELIVERY_TERM_OPTIONS,
            width=30,
        )
        combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        self.section_vars = {}
        self.section_text_widgets = {}

        # Define optional sections
        checks = [
            ("include_coo_requirement_line", "Certificate of Origin Requirement Line", "coo_requirement_text", 2),
            ("include_inspection_requirement_line", "3rd Party Inspection Requirement Line", "inspection_requirement_text", 2),
            ("include_inspection_section", "3rd Party Inspection Section Details", "inspection_section_text", 4),
            ("include_coo_section", "Certificate of Origin (COO) Section Details", "coo_section_text", 3),
            ("include_general_note", "General Note Section Details", "general_note_text", 3),
            ("include_country_of_origin", "Country of Origin Section Details (e.g. Italy, Germany, Spain)", "country_of_origin_text", 3),
        ]

        row_idx = 1
        for key, label, text_key, height in checks:
            # Checkbox
            var = tk.BooleanVar(value=True if "country_of_origin" not in key else False)
            chk = ttk.Checkbutton(sec, text=f"Include {label}", variable=var)
            chk.grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=5, pady=(8, 2))
            self.section_vars[key] = var

            # Editable Text Box underneath
            txt = scrolledtext.ScrolledText(sec, height=height, width=80, wrap="word")
            txt.grid(row=row_idx + 1, column=0, columnspan=2, sticky="ew", padx=(25, 5), pady=(0, 5))
            self.section_text_widgets[text_key] = txt

            # Trace helper to enable/disable
            def make_toggle_handler(v, t):
                def handler(*_):
                    if v.get():
                        t.config(state="normal", bg="white")
                    else:
                        t.config(state="disabled", bg="#f0f0f0")
                return handler

            var.trace_add("write", make_toggle_handler(var, txt))
            
            # Initial state trigger
            make_toggle_handler(var, txt)()
            
            row_idx += 2

        # Packing text
        ttk.Label(sec, text="Packing Header:").grid(
            row=row_idx, column=0, sticky="w", padx=5, pady=3
        )
        self.packing_header_var = tk.StringVar()
        ttk.Entry(
            sec, textvariable=self.packing_header_var, width=40
        ).grid(row=row_idx, column=1, sticky="w", padx=5, pady=3)

        ttk.Label(sec, text="Packing Text:").grid(
            row=row_idx + 1, column=0, sticky="w", padx=5, pady=3
        )
        self.packing_text_var = tk.StringVar()
        ttk.Entry(
            sec, textvariable=self.packing_text_var, width=60
        ).grid(row=row_idx + 1, column=1, sticky="w", padx=5, pady=3)

        # Custom notes
        ttk.Label(sec, text="Custom Notes (added to scope):").grid(
            row=row_idx + 2, column=0, sticky="nw", padx=5, pady=3
        )
        self.custom_notes_text = scrolledtext.ScrolledText(
            sec, width=65, height=3, wrap="word"
        )
        self.custom_notes_text.grid(
            row=row_idx + 2, column=1, padx=5, pady=3
        )

    def _build_output_section(self) -> None:
        """Build the output configuration section."""
        sec = ttk.LabelFrame(self.inner, text="Output", padding=10)
        sec.pack(fill="x", padx=10, pady=(5, 15))

        # Split RFQs checkbox
        self.split_var = tk.BooleanVar()
        ttk.Checkbutton(
            sec,
            text="Generate manufacturer-specific split RFQs",
            variable=self.split_var,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=5, pady=3)

        # Engineer name (combobox with stored names)
        ttk.Label(sec, text="Engineer Name:").grid(
            row=1, column=0, sticky="w", padx=5, pady=3
        )
        stored_names = self.settings.get("engineer_names", [])
        self.engineer_var = tk.StringVar()
        self.engineer_combo = ttk.Combobox(
            sec,
            textvariable=self.engineer_var,
            values=stored_names,
            width=35,
        )
        self.engineer_combo.grid(
            row=1, column=1, sticky="w", padx=5, pady=3
        )

        # Output filename
        ttk.Label(sec, text="Filename:").grid(
            row=2, column=0, sticky="w", padx=5, pady=3
        )
        self.filename_var = tk.StringVar()
        ttk.Entry(sec, textvariable=self.filename_var, width=55).grid(
            row=2, column=1, sticky="w", padx=5, pady=3
        )
        ttk.Label(sec, text=".docx / .pdf", foreground="gray").grid(
            row=2, column=2, sticky="w"
        )

        # Output folder
        ttk.Label(sec, text="Output Folder:").grid(
            row=3, column=0, sticky="w", padx=5, pady=3
        )
        self.output_folder_var = tk.StringVar()
        ttk.Entry(sec, textvariable=self.output_folder_var, width=55).grid(
            row=3, column=1, sticky="w", padx=5, pady=3
        )
        ttk.Button(
            sec, text="Browse…", command=self._browse_output_folder
        ).grid(row=3, column=2, padx=5)

        # Raw extracted text viewer (collapsible)
        raw_frame = ttk.LabelFrame(
            self.inner, text="Raw Extracted Text (for reference)", padding=5
        )
        raw_frame.pack(fill="x", padx=10, pady=(0, 15))

        self.raw_text_widget = scrolledtext.ScrolledText(
            raw_frame, width=80, height=6, wrap="word", state="disabled"
        )
        self.raw_text_widget.pack(fill="x")

    # ------------------------------------------------------------------
    # Populate review screen with extracted data
    # ------------------------------------------------------------------

    def _populate_review_screen(self) -> None:
        d = self.rfq_data

        # Header fields
        self.header_vars["ref_number"].set(d.ref_number)
        self.header_vars["tender_subject"].set(d.tender_subject)
        
        if d.closing_date:
            from datetime import datetime
            parsed_dt = None
            for fmt in ("%d.%m.%Y", "%Y.%m.%d", "%d-%m-%Y", "%Y-%m-%d"):
                try:
                    parsed_dt = datetime.strptime(d.closing_date.strip(), fmt)
                    break
                except ValueError:
                    continue
            if parsed_dt:
                self.closing_date_entry.set_date(parsed_dt.date())

        # Optional fields
        for key, (check_var, val_var, toggle_key) in self.optional_vars.items():
            check_var.set(getattr(d, toggle_key, False))
            val_var.set(getattr(d, key, ""))

        # Items table
        self.items_tree.delete(*self.items_tree.get_children())
        for item in d.items:
            # Replace newlines for Treeview display
            desc_clean = item.description.replace("\n", " | ").replace("\r", "")
            desc_display = desc_clean[:120]
            if len(desc_clean) > 120:
                desc_display += "…"
            self.items_tree.insert(
                "",
                "end",
                values=(item.index, desc_display, item.quantity),
            )

        # Template options
        self.delivery_var.set(d.delivery_terms)
        for key, var in self.section_vars.items():
            val = getattr(d, key, False if "country_of_origin" in key else True)
            var.set(val)

        # Pre-fill editable section text widgets
        text_keys = [
            ("coo_requirement_text", "coo_requirement_text"),
            ("inspection_requirement_text", "inspection_requirement_text"),
            ("inspection_section_text", "inspection_section_text"),
            ("coo_section_text", "coo_section_text"),
            ("general_note_text", "general_note_text"),
            ("country_of_origin_text", "country_of_origin_text"),
        ]
        
        for text_key, rfq_field in text_keys:
            widget = self.section_text_widgets.get(text_key)
            if widget:
                # Load custom default from settings if not set on rfq_data
                val = getattr(d, rfq_field, "")
                if not val.strip():
                    val = self.settings.get(rfq_field, "")
                
                setattr(d, rfq_field, val)
                
                widget.config(state="normal")
                widget.delete("1.0", "end")
                widget.insert("1.0", val)
                # Dynamically size box height to fit number of lines
                lines_count = len(val.splitlines())
                widget.config(height=max(3, min(12, lines_count + 1)))
                
                # Check toggle state to set enabled/disabled color
                toggle_key = rfq_field.replace("_text", "")
                if "coo_requirement" in rfq_field:
                    toggle_key = "include_coo_requirement_line"
                elif "inspection_requirement" in rfq_field:
                    toggle_key = "include_inspection_requirement_line"
                elif "inspection_section" in rfq_field:
                    toggle_key = "include_inspection_section"
                elif "coo_section" in rfq_field:
                    toggle_key = "include_coo_section"
                elif "general_note" in rfq_field:
                    toggle_key = "include_general_note"
                elif "country_of_origin" in rfq_field:
                    toggle_key = "include_country_of_origin"
                    
                is_checked = getattr(d, toggle_key, True if "country_of_origin" not in toggle_key else False)
                if not is_checked:
                    widget.config(state="disabled", bg="#f0f0f0")
                else:
                    widget.config(state="normal", bg="white")

        self.packing_header_var.set(d.packing_header)
        # Pre-fill packing text from settings if empty
        p_text = d.packing_text
        if not p_text.strip():
            p_text = self.settings.get("packing_text", "As per manufacturer standards.")
        self.packing_text_var.set(p_text)
        d.packing_text = p_text

        self.custom_notes_text.delete("1.0", "end")
        if d.custom_notes:
            self.custom_notes_text.insert("1.0", "\n".join(d.custom_notes))

        # Output
        self.split_var.set(d.generate_split_rfqs)
        self.engineer_var.set(d.engineer_name)
        self.filename_var.set(d.output_filename)
        self.output_folder_var.set(d.output_folder)

        # Raw text
        self.raw_text_widget.config(state="normal")
        self.raw_text_widget.delete("1.0", "end")
        self.raw_text_widget.insert("1.0", d.raw_extracted_text[:5000])
        self.raw_text_widget.config(state="disabled")

    # ------------------------------------------------------------------
    # Items table actions
    # ------------------------------------------------------------------

    def _add_item(self) -> None:
        dlg = ItemDialog(self.root, title="Add Item")
        if dlg.result:
            item = dlg.result
            item.index = len(self.items_tree.get_children()) + 1
            self.rfq_data.items.append(item)
            desc_display = item.description[:120]
            if len(item.description) > 120:
                desc_display += "…"
            self.items_tree.insert(
                "", "end", values=(item.index, desc_display, item.quantity)
            )

    def _edit_item(self) -> None:
        sel = self.items_tree.selection()
        if not sel:
            messagebox.showinfo("Select", "Please select an item to edit.")
            return

        idx = self.items_tree.index(sel[0])
        item = self.rfq_data.items[idx]

        dlg = ItemDialog(self.root, item=item, title="Edit Item")
        if dlg.result:
            dlg.result.index = item.index
            self.rfq_data.items[idx] = dlg.result
            desc_display = dlg.result.description[:120]
            if len(dlg.result.description) > 120:
                desc_display += "…"
            self.items_tree.item(
                sel[0],
                values=(dlg.result.index, desc_display, dlg.result.quantity),
            )

    def _remove_item(self) -> None:
        sel = self.items_tree.selection()
        if not sel:
            return
        idx = self.items_tree.index(sel[0])
        self.rfq_data.items.pop(idx)
        self.items_tree.delete(sel[0])
        # Re-number
        for i, iid in enumerate(self.items_tree.get_children(), 1):
            vals = list(self.items_tree.item(iid, "values"))
            vals[0] = i
            self.items_tree.item(iid, values=vals)
            if i - 1 < len(self.rfq_data.items):
                self.rfq_data.items[i - 1].index = i

    def _move_item(self, direction: int) -> None:
        sel = self.items_tree.selection()
        if not sel:
            return
        idx = self.items_tree.index(sel[0])
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.rfq_data.items):
            return
        # Swap in data
        self.rfq_data.items[idx], self.rfq_data.items[new_idx] = (
            self.rfq_data.items[new_idx],
            self.rfq_data.items[idx],
        )
        # Refresh table
        self._refresh_items_tree()

    def _refresh_items_tree(self) -> None:
        self.items_tree.delete(*self.items_tree.get_children())
        for i, item in enumerate(self.rfq_data.items, 1):
            item.index = i
            desc_clean = item.description.replace("\n", " | ").replace("\r", "")
            desc_display = desc_clean[:120]
            if len(desc_clean) > 120:
                desc_display += "…"
            self.items_tree.insert(
                "", "end", values=(i, desc_display, item.quantity)
            )

    # ------------------------------------------------------------------
    # Output folder
    # ------------------------------------------------------------------

    def _browse_output_folder(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.output_folder_var.get(),
        )
        if folder:
            self.output_folder_var.set(folder)

    # ==================================================================
    # SCREEN 3: Progress
    # ==================================================================

    def _build_progress_screen(self) -> None:
        frame = ttk.Frame(self.container, padding=30)
        self.screens["progress"] = frame

        ttk.Label(
            frame,
            text="Generation Progress",
            font=("Segoe UI", 16, "bold"),
        ).pack(pady=(20, 10))

        self.progress_bar = ttk.Progressbar(
            frame, mode="indeterminate", length=500
        )
        self.progress_bar.pack(pady=10)

        self.progress_log = scrolledtext.ScrolledText(
            frame, width=80, height=15, wrap="word", state="disabled"
        )
        self.progress_log.pack(fill="both", expand=True, pady=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)

        self.open_folder_btn = ttk.Button(
            btn_frame,
            text="Open Output Folder",
            command=self._open_output_folder,
            state="disabled",
        )
        self.open_folder_btn.pack(side="left", padx=10)

        ttk.Button(
            btn_frame,
            text="Process Another",
            command=self._process_another,
        ).pack(side="left", padx=10)

    def _log_progress(self, msg: str) -> None:
        """Thread-safe logging to the progress text widget."""
        def _update():
            self.progress_log.config(state="normal")
            self.progress_log.insert("end", msg + "\n")
            self.progress_log.see("end")
            self.progress_log.config(state="disabled")
        self.root.after(0, _update)

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        """Collect all form data and trigger RFQ generation."""
        # Collect data from form back into rfq_data
        d = self.rfq_data
        d.ref_number = self.header_vars["ref_number"].get().strip()
        d.tender_subject = self.header_vars["tender_subject"].get().strip()
        d.closing_date = self.closing_date_entry.get().strip()

        for key, (check_var, val_var, toggle_key) in self.optional_vars.items():
            setattr(d, toggle_key, check_var.get())
            setattr(d, key, val_var.get().strip())

        d.delivery_terms = self.delivery_var.get().strip()
        for key, var in self.section_vars.items():
            setattr(d, key, var.get())

        # Read back editable section details
        for text_key, widget in self.section_text_widgets.items():
            setattr(d, text_key, widget.get("1.0", "end-1c").strip())

        d.packing_header = self.packing_header_var.get().strip()
        d.packing_text = self.packing_text_var.get().strip()

        custom = self.custom_notes_text.get("1.0", "end-1c").strip()
        d.custom_notes = [ln for ln in custom.splitlines() if ln.strip()] if custom else []

        d.generate_split_rfqs = self.split_var.get()
        d.engineer_name = self.engineer_var.get().strip()
        d.output_filename = self.filename_var.get().strip()
        d.output_folder = self.output_folder_var.get().strip()

        # Validation
        if not d.ref_number:
            messagebox.showwarning("Missing", "Ref. # is required.")
            return
        if not d.tender_subject:
            messagebox.showwarning("Missing", "Tender Subject is required.")
            return
        if not d.output_folder:
            messagebox.showwarning("Missing", "Output folder is required.")
            return
        if not d.engineer_name:
            messagebox.showwarning("Missing", "Engineer name is required.")
            return

        # Save engineer name to settings
        add_engineer_name(self.settings, d.engineer_name)
        save_settings(self.settings)

        # Switch to progress screen
        self._show("progress")
        self.progress_log.config(state="normal")
        self.progress_log.delete("1.0", "end")
        self.progress_log.config(state="disabled")
        
        # Reset to indeterminate and animate
        self.progress_bar.config(mode="indeterminate", value=0)
        self.progress_bar.start(10)
        self.open_folder_btn.config(state="disabled")

        # Run generation in background thread
        threading.Thread(
            target=self._generate_thread, daemon=True
        ).start()

    def _generate_thread(self) -> None:
        """Run the RFQ builder in a background thread."""
        try:
            template_path = get_template_path()
            self._log_progress(f"Template: {os.path.basename(template_path)}")

            from processors.rfq_builder import RFQBuilder

            builder = RFQBuilder(template_path, log_callback=self._log_progress)
            output_path = builder.build(self.rfq_data)

            self.root.after(0, self._generation_done, output_path)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.root.after(0, self._generation_error, str(e), tb)

    def _generation_done(self, output_path: str) -> None:
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", value=100)  # Fill bar to 100%
        self._log_progress("\n✓ RFQ generation complete!")
        self._log_progress(f"Output: {output_path}")
        self.open_folder_btn.config(state="normal")

    def _generation_error(self, error: str, traceback_str: str) -> None:
        self.progress_bar.stop()
        self._log_progress(f"\n✗ Error: {error}")
        self._log_progress(traceback_str)
        messagebox.showerror("Generation Error", error)

    def _open_output_folder(self) -> None:
        folder = self.rfq_data.output_folder
        if folder and os.path.isdir(folder):
            os.startfile(folder)

    def _process_another(self) -> None:
        self.rfq_data = RFQData()
        self.file_path_var.set("")
        self.file_status_var.set("Ready")
        self._show("file")

    def _open_settings(self) -> None:
        """Launch the global settings configuration dialog."""
        SettingsDialog(self.root)
        # Reload settings and update dropdown options in GUI
        self.settings = load_settings()
        stored_names = self.settings.get("engineer_names", [])
        self.engineer_combo.config(values=stored_names)
        if stored_names:
            self.engineer_var.set(stored_names[0])


# ======================================================================
# Entry point
# ======================================================================

def run_app():
    root = tk.Tk()
    root.iconbitmap(default="")  # Use default icon

    # Apply a modern theme
    style = ttk.Style()
    available = style.theme_names()
    if "vista" in available:
        style.theme_use("vista")
    elif "clam" in available:
        style.theme_use("clam")

    RFQApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_app()
