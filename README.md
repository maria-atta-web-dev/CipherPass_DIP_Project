# CipherPass

**CipherPass** is a Pakistani banking KYC and AML screening prototype that demonstrates CNIC image verification, biometric face capture, digital image processing, criminal record screening, and compliance decision workflows.

## Project Overview

This system is built as an educational proof-of-concept for banks and financial institutions in Pakistan. It combines:
- CNIC validation and formatting checks
- Digital Image Processing (DIP) on CNIC images
- Face capture and biometric liveness analysis
- Criminal/AML database screening
- Duplicate verification detection
- Trust scoring and compliance review actions
- PDF report export and archive history storage

## Technology Stack

- Python 3.x
- PyQt5 (Graphical User Interface)
- OpenCV (`opencv-python-headless`)
- NumPy
- Pillow
- ReportLab

## Requirements

Install the required Python packages from `requirements.txt`:

```bash
pip install -r requirements.txt
```

> Note: If you experience webcam or GUI issues with `opencv-python-headless`, you may replace it with `opencv-python`.

## Initial Setup

1. Clone or extract the repository into a local folder.
2. Open a terminal in the project folder `CipherPass`.
3. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Confirm the following files exist:
- `main.py`
- `requirements.txt`
- `citizen_database.json`
- `criminal_records.json`
- `verification_data/` (created automatically when the app runs)

## Running the Application

From the project root folder, launch the GUI:

```bash
python main.py
```

The app opens a dashboard with the following workflow:
1. Enter or lookup a CNIC.
2. Upload CNIC images and/or capture a live face image.
3. Start verification to run DIP, AML screening, and scoring.
4. If the customer is flagged, use the compliance review dialog.
5. Save results and export reports as needed.

## Main Features

- **Pakistan CNIC validation** using NADRA-style formatting
- **Digital Image Processing pipeline** for CNIC images
- **Live face capture** and biometric face detection
- **Criminal record screening** using `criminal_records.json`
- **Duplicate verification detection** using `verification_data/history.json`
- **Trust score calculation** and risk classification
- **Compliance officer actions** including `REPORT_FIA`, `REJECT`, `ESCALATE`, and `HOLD`
- **PDF export** for verification reports
- **Archive storage** of filtered CNIC images and session history

## Core Files

- `main.py` — main application and GUI flow
- `dip_pipeline.py` — digital image processing demo pipeline
- `cnic_processor.py` — CNIC image normalization and enhancement
- `face_module.py` — face verification and liveness scoring
- `document_module.py` — CNIC authenticity analysis
- `customer_screening.py` — AML and criminal lookup logic
- `scoring.py` — trust scoring and risk assessment
- `cnic_archive.py` — archive and history storage
- `pdf_export.py` — PDF report generation
- `ui_styles.py` — application styling
- `pakistan_kyc.py` — Pakistani CNIC validation helpers
- `utils.py` — utility functions

## Data Files

- `citizen_database.json` — sample bank customer records
- `criminal_records.json` — simulated FIA/AML watchlist
- `verification_data/history.json` — generated verification history
- `verification_data/compliance_decisions.json` — saved compliance decisions
- `verification_data/cnic_archive/` — saved CNIC snapshot archives

## Adding Project Images to README

If you want to display screenshots in this README, add images to a folder such as `docs/images/` and update the paths below.

Example placeholders:

```markdown
![CipherPass Dashboard](docs/images/dashboard.png)
![CNIC Verification](docs/images/cnic-verification.png)
![DIP Pipeline](docs/images/dip-pipeline.png)
```

### Suggested image captions
- `dashboard.png` — main dashboard showing live verification stats
- `cnic-verification.png` — CNIC upload and lookup screen
- `dip-pipeline.png` — digital image processing steps display

## Suggested Screenshot Paths

- `docs/images/dashboard.png`
- `docs/images/cnic-verification.png`
- `docs/images/dip-pipeline.png`

> Tip: Create these images by taking screenshots of the running app and saving them into `docs/images/`.

## Usage Notes

- Ensure your webcam is connected if you want live face capture.
- Run `main.py` from the repository root so the application can access the JSON data files.
- If the app creates no `verification_data` folder, it will be generated automatically on the first successful verification.

## Example CNICs for Testing

- `42101-1234567-1` — clean profile, expected approval
- `12345-6789012-3` — identity fraud, review/reject
- `11111-2222222-3` — criminal record, reject

## Project Purpose

This project is designed to demonstrate how a Pakistani bank or financial service could integrate:
- KYC document validation
- AML criminal screening
- digital image forensics
- biometric face checks
- compliance decision tracking

## Credits

Built as a final project for Digital Image Processing and AML/KYC screening concepts.

---

For additional notes, see `PROJECT_REPORT.txt` and `VIVA_GUIDE.md`.
