# OCR Receipt Scanning – Design & Implementation Guide

**Status**: 📋 Planned (not yet implemented)  
**Priority**: Medium  
**Created**: 2026-02-23

---

## Overview

This document describes the planned OCR integration for scanning fuel receipts (photos and PDFs) within haFWCMA. The goal is to allow users to upload a receipt image or PDF alongside a FuelLog entry, have the system automatically extract key refueling data via OCR, and pre-fill the FuelLog edit form with the recognised values.

---

## Feature Requirements

### Upload channels
- **Telegram**: Send a photo or PDF document to the Telegram bot; the bot associates it with the most recent (or active) refueling entry.
- **FuelLog Edit Dialog**: Drag-and-drop or file-picker upload directly in the card UI.

### Data extracted by OCR
| Field              | Example value      |
|--------------------|--------------------|
| Station name       | "Shell Autobahn A9"|
| Date               | 2026-02-23         |
| Time               | 14:35              |
| Litres refueled    | 42.15 L            |
| Price per litre    | 1.849 €/L          |
| Total cost         | 77.93 €            |
| Fuel type          | Super E10          |
| Address            | Musterstr. 1, …    |

### Storage per refueling record
```json
{
  "receipt": {
    "file_path": "www/hafwcma_receipts/<entry_id>.<ext>",
    "mime_type": "image/jpeg",
    "ocr_raw_text": "…full raw OCR output…",
    "ocr_fields": { "station_name": "Shell", "litres": 42.15, … },
    "ocr_engine": "paddleocr",
    "document_quality": "good",
    "confidence": 0.87,
    "processed_at": "2026-02-23T14:40:00+01:00"
  }
}
```

### UI elements
- **Receipt preview** button in FuelLog edit dialog (opens image/PDF in a lightbox or new tab).
- OCR raw output tab (collapsible) next to the parsed fields.
- Confidence badge per pre-filled field (green ≥ 0.8, yellow 0.5–0.8, red < 0.5).

### Backup & restore
Receipt files are stored in `<config>/www/hafwcma_receipts/` and included in the existing backup ZIP created by `utils/backup_manager.py`.

---

## OCR Engine Comparison

### Local engines (preferred – no cloud dependency, open-source)

| Engine     | Licence   | Strengths                                     | Notes                                    |
|------------|-----------|-----------------------------------------------|------------------------------------------|
| **PaddleOCR** | Apache 2.0 | KI-based, layout + table recognition, Python API, RPi/x86 | Best overall choice; install: `pip install paddlepaddle paddleocr` |
| **DocTR**   | Apache 2.0 | Transformer-OCR, excellent layout recognition | `pip install python-doctr[torch]`        |
| **EasyOCR** | Apache 2.0 | Easy to integrate, 80+ languages              | `pip install easyocr` — simpler fallback |

#### Recommended local approach
Use **PaddleOCR** as the primary engine. Fall back to **EasyOCR** if PaddleOCR cannot be installed (e.g., unsupported architecture).

#### Installation note for Home Assistant
These packages are **not bundled** with haFWCMA because they are large (100 MB – 1 GB). Users must install them manually in their HA Python environment or via a custom add-on / virtual environment.

Provide a persistent notification + setup guide link when OCR is enabled but the required package is missing.

---

### Cloud OCR services (configurable via API key)

All cloud services require an API key that the user must configure in the Options Flow.

#### 2.1 Google Cloud Vision / Document AI
- **Type**: KI-OCR + Document AI  
- **Strengths**: Extremely high accuracy on receipts; extracts structured fields  
- **Pricing**: Pay-per-page; first 1 000 units/month free  
- **Getting an API key**:
  1. Go to [console.cloud.google.com](https://console.cloud.google.com/) and create a project.
  2. Enable the **Cloud Vision API** (and optionally **Document AI**).
  3. Create a Service Account key (JSON) or an API key under *Credentials*.
  4. Enter the key (or JSON path) in the haFWCMA Options Flow → OCR settings.
- **Docs**: https://cloud.google.com/vision/docs/receipt-understanding

#### 2.2 Microsoft Azure Cognitive Services (Form Recognizer / Receipt model)
- **Type**: KI-OCR + Layout + dedicated Receipt model  
- **Strengths**: Purpose-built Receipt model extracts date, total, tax, merchant, line items  
- **Pricing**: Pay-per-page; free tier available  
- **Getting an API key**:
  1. Sign in to [portal.azure.com](https://portal.azure.com/).
  2. Create a **Form Recognizer** (now called *Azure AI Document Intelligence*) resource.
  3. Copy **Endpoint** and **Key 1** from the resource overview.
  4. Enter both in haFWCMA Options Flow → OCR settings.
- **Docs**: https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-receipt

#### 2.3 AWS Textract
- **Type**: KI-OCR + Layout + Tables  
- **Strengths**: Very good on structured documents; returns key-value pairs  
- **Pricing**: Pay-per-page; some free tier available  
- **Getting an API key**:
  1. Sign in to [aws.amazon.com](https://aws.amazon.com/) and open IAM.
  2. Create a user with `textract:AnalyzeDocument` / `textract:DetectDocumentText` permissions.
  3. Generate an **Access Key ID** + **Secret Access Key**.
  4. Enter both (+ AWS region) in haFWCMA Options Flow → OCR settings.
- **Docs**: https://docs.aws.amazon.com/textract/latest/dg/what-is.html

---

## Config/Options Flow changes required

Add a new **OCR** section to the Options Flow (`config_flow.py`) with the following fields:

```python
vol.Optional(CONF_OCR_ENGINE, default="none"):
    vol.In(["none", "paddleocr", "doctr", "easyocr",
            "google_vision", "azure_form_recognizer", "aws_textract"])

# Cloud fields (shown conditionally)
vol.Optional(CONF_OCR_GOOGLE_API_KEY): cv.string
vol.Optional(CONF_OCR_AZURE_ENDPOINT): cv.string
vol.Optional(CONF_OCR_AZURE_KEY): cv.string
vol.Optional(CONF_OCR_AWS_ACCESS_KEY): cv.string
vol.Optional(CONF_OCR_AWS_SECRET_KEY): cv.string
vol.Optional(CONF_OCR_AWS_REGION, default="eu-central-1"): cv.string
```

Constants to add in `const.py`:
```python
CONF_OCR_ENGINE = "ocr_engine"
CONF_OCR_GOOGLE_API_KEY = "ocr_google_api_key"
CONF_OCR_AZURE_ENDPOINT = "ocr_azure_endpoint"
CONF_OCR_AZURE_KEY = "ocr_azure_key"
CONF_OCR_AWS_ACCESS_KEY = "ocr_aws_access_key"
CONF_OCR_AWS_SECRET_KEY = "ocr_aws_secret_key"
CONF_OCR_AWS_REGION = "ocr_aws_region"
```

---

## Implementation Plan

### Phase 1 – File upload & storage
- [ ] HTTP endpoint `POST /api/hafwcma/upload_receipt` (similar to `backup_http_views.py`)
- [ ] Save file to `<config>/www/hafwcma_receipts/<refueling_id>.<ext>`
- [ ] Store `receipt.file_path` in the refueling record
- [ ] Include `hafwcma_receipts/` in backup/restore logic

### Phase 2 – Telegram upload
- [ ] Handle `document` and `photo` message types in `telegram_refueling_handler.py`
- [ ] Download file via Telegram Bot API and save to `hafwcma_receipts/`
- [ ] Associate with matching refueling record (by timestamp proximity)

### Phase 3 – Local OCR processing
- [ ] Create `utils/ocr_engine.py` with a common `OCREngine` protocol
- [ ] Implement `PaddleOCREngine`, `DocTROCREngine`, `EasyOCREngine` adapters
- [ ] Receipt field extractor: regex + heuristic parsing of raw OCR text
- [ ] Quality scorer: based on text density, language confidence, field coverage
- [ ] Store results in `receipt.ocr_*` fields of the refueling record

### Phase 4 – Cloud OCR processing
- [ ] Implement `GoogleVisionEngine`, `AzureFormRecognizerEngine`, `AWSTextractEngine`
- [ ] Validate API keys during Options Flow (test request on save)

### Phase 5 – UI integration
- [ ] Receipt upload drag-and-drop in FuelLog Edit dialog (`fwcam-card.js`)
- [ ] Receipt preview button / lightbox
- [ ] OCR confidence badges on pre-filled form fields
- [ ] Collapsible "OCR raw output" section

---

## Notes & Open Questions

- PaddleOCR and DocTR models are large (several hundred MB). Consider lazy-loading or a clear user notification.
- PDF support requires `pdf2image` + `poppler` or `pypdfium2` as an additional dependency.
- Receipt OCR output may be in German, which all three local engines support natively.
- Privacy: receipt images may contain personal data (plate numbers, loyalty cards). Add a note in the UI.
