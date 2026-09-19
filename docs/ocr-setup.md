# OCR Setup

PDFs with a usable text layer do not require Tesseract. JPG/PNG uploads and scanned PDFs do.

## Verify readiness

Start the backend and open:

```text
http://localhost:8000/api/health
```

The response includes:

- `ocr_available`
- `tesseract_version`
- `ocr_error`
- `pdf_text_extraction_available`

## Install Tesseract

Install the Tesseract executable using the package manager or official distribution for your operating system, then ensure the `tesseract` command is on `PATH` before starting Uvicorn.

Windows PowerShell example with WinGet:

```powershell
winget install --id UB-Mannheim.TesseractOCR
```

macOS:

```bash
brew install tesseract
```

Debian/Ubuntu:

```bash
sudo apt-get install tesseract-ocr
```

Restart the backend after installation. If the executable cannot be found, the application remains usable for text-based PDFs and reports a clear OCR-unavailable error for image uploads.
