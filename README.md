# RFQ Automation Tool 🚀

An intelligent, multi-format desktop automation software designed to streamline the extraction of customer inquiry data and the generation of standardized **Request for Quotation (RFQ)** documents in Word (`.docx`) and PDF formats.

---

## 📌 Overview

The **RFQ Automation Tool** replaces manual document creation for engineering inquiries. It ingests supplier and client RFQs provided in various file formats (`.msg`, `.pdf`, `.xlsx`, `.docx`), parses line items, technical specifications, closing dates, and tender metadata, and populates a master template document.

### Key Capabilities
- **Multi-Format Extraction**: Parses Outlook emails (`.msg`), PDFs (native & scanned), Excel sheets (`.xlsx`/`.xls`), and Word documents (`.docx`).
- **OCR & Translation**: Uses Optical Character Recognition (pytesseract) for scanned PDFs and includes automated Arabic-to-English translation with an interactive human-in-the-loop review interface.
- **Structured Data Extraction**: Tailored parsers for specialized inquiry formats (such as structured RFx material specifications, engineering field data sheets, and direct email inquiries).
- **Template-Based Generation**: Fills master `.docx` templates and formats items sequentially or grouped by manufacturer.
- **Manufacturer-Split RFQs**: Option to automatically split multi-brand inquiries into separate, vendor-specific RFQ documents.
- **Word-to-PDF Conversion**: Native Microsoft Word COM automation for high-fidelity PDF rendering.
- **Batch Processing & Interactive Wizard**: 3-step desktop GUI (File Input → Review & Edit → Progress & Output).

---

## 🏗️ Repository Structure

```
Program/
├── .gitignore               # Git ignore rules for Python, PyInstaller, and OS artifacts
├── README.md                # Project documentation and quickstart guide
├── PROJECT_CONTEXT.md       # Comprehensive architectural context file for LLMs
└── scso_rfq_tool/           # Main Python application package
    ├── main.py              # Application entry point & runtime initialization
    ├── build.spec           # PyInstaller build specification file
    ├── installer.iss        # Inno Setup Windows installer compiler script
    ├── requirements.txt     # Python package dependencies
    ├── config/
    │   └── settings.py      # Persistent user settings and template text configurations
    ├── extractors/          # File parsing subsystem
    │   ├── base.py          # Abstract extractor interface
    │   ├── docx_extractor.py # Word document parser
    │   ├── msg_extractor.py  # Outlook email & attachment parser
    │   ├── pdf_extractor.py  # PDF text, OCR, & translation parser
    │   └── xlsx_extractor.py # Excel spreadsheet parser
    ├── gui/
    │   └── app.py           # Tkinter desktop GUI (Wizard screens & dialogs)
    ├── models/
    │   └── rfq_data.py      # Core data models (RFQItem & RFQData)
    ├── processors/
    │   └── rfq_builder.py   # Document generation engine & PDF converter
    └── resources/
        └── SCSO RFQ.docx    # Sample Word RFQ template
```

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.10+** (64-bit recommended)
- **Microsoft Word** (installed locally for PDF export features)
- *(Optional)* **Tesseract OCR**: Installed and added to system `PATH` if OCR for scanned PDFs is needed.

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/mo-raaed/scso-rfq-tool.git
   cd scso-rfq-tool
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python -m venv .venv
   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # On Windows (CMD):
   .venv\Scripts\activate.bat
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r scso_rfq_tool/requirements.txt
   ```

---

## 🚀 Running the Application

To start the application from source code:

```bash
python scso_rfq_tool/main.py
```

---

## 📦 Packaging & Distribution

### 1. Build Executable with PyInstaller
To build a standalone single-folder Windows application:

```bash
cd scso_rfq_tool
pyinstaller build.spec
```
The compiled executable will be located at `dist/SCSO_RFQ_Tool/SCSO RFQ Tool.exe`.

### 2. Create Windows Installer with Inno Setup
1. Ensure [Inno Setup](https://jrsoftware.org/isinfo.php) is installed.
2. Open `scso_rfq_tool/installer.iss` in Inno Setup Compiler.
3. Click **Compile** (or press `Ctrl + F9`).
4. The output installer `SCSO_RFQ_Tool_Setup_v1.0.0.exe` will be generated in `scso_rfq_tool/installer_output/`.

---

## ⚙️ Configuration & Customization

User configurations are saved automatically to `~/.scso_rfq_tool/settings.json`. You can modify defaults directly through the GUI **Settings** menu:
- **Saved Engineer Names**: Dropdown memory for sales and project engineers.
- **Default Delivery Terms**: e.g., `Ex-Work, FOB, FCA.`
- **Default Clause Texts**: Certificate of Origin (COO), 3rd Party Inspection, General Notes, and Country of Origin requirement texts.

---

## 📄 Documentation for LLMs

If you are feeding this codebase to another AI model for context, please refer to [PROJECT_CONTEXT.md](file:///c:/Users/asus/Documents/AUIS/Summer%202026/ENGR%20490/Program/PROJECT_CONTEXT.md), which contains complete system specifications, data models, parsing algorithms, and architectural breakdowns.

---

## 📜 License

Demonstration & Portfolio Showcase — Built for Engineering & Procurement Operations.

