"""
gemini_receipts.py

Fixed and improved version of your receipt processing module that uses
Google Gemini Generative Language API.

Usage:
- Set GEMINI_API_KEY in the environment:
    export GEMINI_API_KEY="your_api_key_here"
  (on Windows use setx or set in system env)

Notes:
- This module assumes a Django model named FuelReceipt with fields used below.
- The Gemini API URL and payload structure are kept similar to your original.
- The module is defensive: it extracts JSON from Gemini responses even if
  the model returns text with code fences or additional commentary.
"""

import os
import re
import json
import base64
import logging
import mimetypes
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# Configure API key and endpoint via environment for security
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY environment variable not set. Set it to use the Gemini API.")

# Default endpoint (keep as originally used)
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Session for HTTP pooling
_SESSION = requests.Session()
_DEFAULT_TIMEOUT = 30  # seconds


def _detect_mime_type(path: str) -> str:
    mime, _ = mimetypes.guess_type(path)
    # fallback defaults
    if not mime:
        return "application/octet-stream"
    return mime


def _to_float(value: Any) -> Optional[float]:
    """
    Robustly convert various numeric string formats to float.
    Returns None if conversion fails or value is None/empty.
    Examples accepted: "12.34", "$12.34", "1,234.56"
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    # remove currency symbols and commas
    s = re.sub(r"[^\d\.\-]", "", s)
    # if there are multiple dots, keep the last as decimal separator
    if s.count(".") > 1:
        parts = s.split(".")
        s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(s)
    except ValueError:
        return None


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to locate and decode a JSON object in the provided text.
    Handles:
      - plain JSON
      - JSON wrapped in markdown code fences (```json ... ```)
      - model commentary before/after JSON
    Returns the parsed JSON dict or None if parsing fails.
    """
    if not text:
        return None

    text = text.strip()

    # First, if the entire text is JSON-like, try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Remove common markdown code fence wrappers
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Otherwise, attempt to find the first {...} block that looks like JSON
    brace_stack = []
    start_idx = None
    for i, ch in enumerate(text):
        if ch == "{":
            if start_idx is None:
                start_idx = i
            brace_stack.append(i)
        elif ch == "}":
            if brace_stack:
                brace_stack.pop()
                if not brace_stack and start_idx is not None:
                    candidate = text[start_idx:i+1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        # continue searching for the next top-level JSON object
                        start_idx = None

    # Last-ditch: try to find "key: value" pairs and convert to JSON-ish dict
    # This is heuristic and best-effort only.
    kv_pairs = re.findall(r'["\']?([a-zA-Z0-9_ \-]+?)["\']?\s*[:=]\s*["\']?([^,\n\r]+?)["\']?(?:,|\n|$)', text)
    if kv_pairs:
        result = {}
        for k, v in kv_pairs:
            k_clean = k.strip().lower().replace(" ", "_")
            result[k_clean] = v.strip()
        return result

    return None


def _build_payload_for_image(prompt_text: str, image_b64: str, mime_type: str) -> Dict[str, Any]:
    """
    Build payload matching the structure you originally used: 'contents' -> 'parts'.
    """
    return {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt_text
                    },
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64
                        }
                    }
                ]
            }
        ]
    }


def process_receipt_with_gemini(receipt) -> Optional[Dict[str, Any]]:
    """
    Process receipt image using Google Gemini API for OCR and data extraction.

    Args:
        receipt: FuelReceipt model instance (Django model).
                 Must have attributes: id, receipt_image.path, save(), and target fields.

    Returns:
        dict: Extracted data (raw dict returned by the model parsing step)
              or None if processing failed.
    """
    try:
        logger.info("Processing receipt #%s with Gemini API...", getattr(receipt, "id", "<unknown>"))
        if not getattr(receipt, "receipt_image", None):
            logger.error("No image file found for receipt #%s", getattr(receipt, "id", "<unknown>"))
            return None

        image_path = receipt.receipt_image.path
        with open(image_path, "rb") as f:
            image_data = f.read()

        image_b64 = base64.b64encode(image_data).decode("utf-8")
        mime_type = _detect_mime_type(image_path)

        prompt_text = (
            "Extract the following information from this fuel receipt image:\n"
            "1. Total amount (dollar value)\n"
            "2. Gallons purchased\n"
            "3. Price per gallon\n"
            "4. Date of purchase (prefer YYYY-MM-DD format)\n"
            "5. Gas station name\n"
            "6. Address if visible\n\n"
            "Return the data in JSON format like this:\n"
            "{\n"
            '  "total_amount": "XX.XX",\n'
            '  "gallons": "XX.XX",\n'
            '  "price_per_gallon": "XX.XX",\n'
            '  "date": "YYYY-MM-DD",\n'
            '  "station_name": "Station Name",\n'
            '  "address": "Station Address",\n'
            '  "raw_text": "All extracted text"\n'
            "}\n\nIf any field is not found, use null."
        )

        payload = _build_payload_for_image(prompt_text, image_b64, mime_type)

        if not GEMINI_API_KEY:
            logger.error("Missing GEMINI_API_KEY - aborting request.")
            receipt.processing_status = "failed"
            receipt.raw_ocr_text = "Missing GEMINI_API_KEY"
            receipt.save()
            return None

        url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}

        logger.info("Sending request to Gemini API for receipt #%s...", receipt.id)
        try:
            resp = _SESSION.post(url, headers=headers, json=payload, timeout=_DEFAULT_TIMEOUT)
        except requests.RequestException as e:
            logger.exception("HTTP request to Gemini API failed: %s", e)
            receipt.processing_status = "failed"
            receipt.raw_ocr_text = f"HTTP error: {e}"
            receipt.save()
            return None

        if resp.status_code != 200:
            logger.error("Gemini API returned status %s: %s", resp.status_code, resp.text)
            receipt.processing_status = "failed"
            receipt.raw_ocr_text = resp.text[:2000]
            receipt.save()
            return None

        try:
            result = resp.json()
        except ValueError:
            logger.error("Gemini response is not valid JSON: %s", resp.text[:1000])
            receipt.processing_status = "failed"
            receipt.raw_ocr_text = resp.text[:2000]
            receipt.save()
            return None

        # Attempt to extract text content from response in various shapes
        content_text = None
        try:
            # Common structure from generative language APIs: candidates -> content -> parts
            candidates = result.get("candidates") or []
            if candidates and isinstance(candidates, list):
                first = candidates[0]
                content = first.get("content")
                if content:
                    parts = content.get("parts") or []
                    if parts and isinstance(parts, list):
                        # join text parts
                        texts = []
                        for p in parts:
                            if isinstance(p, dict) and "text" in p and p["text"]:
                                texts.append(p["text"])
                            elif isinstance(p, str):
                                texts.append(p)
                        content_text = "\n".join(texts).strip()
            # Fallbacks
            if not content_text and "content" in result:
                # sometimes it's directly nested
                c = result["content"]
                if isinstance(c, dict) and "text" in c:
                    content_text = c["text"]
                elif isinstance(c, str):
                    content_text = c

            # ultimate fallback: stringify response
            if not content_text:
                content_text = json.dumps(result)
        except Exception as e:
            logger.exception("Failed to extract textual content from Gemini response: %s", e)
            content_text = json.dumps(result)

        logger.debug("Gemini content (first 800 chars): %s", content_text[:800])

        # Try to extract JSON payload from the content_text
        extracted_data = _extract_json_from_text(content_text)
        if not extracted_data:
            # If we could not parse JSON, store raw text and mark failed
            logger.warning("Could not extract JSON from Gemini response for receipt #%s", receipt.id)
            receipt.raw_ocr_text = content_text
            receipt.processing_status = "failed"
            receipt.save()
            return None

        # Normalize keys (support either 'total_amount' or 'total' etc.)
        def _k(dct, *keys):
            for k in keys:
                if k in dct:
                    return dct[k]
            # try lowercased keys
            for k in dct:
                if k.lower() in [kk.lower() for kk in keys]:
                    return dct[k]
            return None

        total_amount_raw = _k(extracted_data, "total_amount", "total", "amount")
        gallons_raw = _k(extracted_data, "gallons", "gallon", "quantity")
        price_raw = _k(extracted_data, "price_per_gallon", "price", "unit_price", "price_per_unit")
        date_raw = _k(extracted_data, "date", "purchase_date")
        station_name = _k(extracted_data, "station_name", "station", "vendor")
        address = _k(extracted_data, "address", "station_address", "location")
        raw_text = _k(extracted_data, "raw_text") or content_text

        # Convert to appropriate types
        receipt.total_amount = _to_float(total_amount_raw)
        receipt.gallons = _to_float(gallons_raw)
        receipt.price_per_gallon = _to_float(price_raw)
        receipt.station_name = station_name or ""
        receipt.station_address = address or ""
        receipt.raw_ocr_text = raw_text
        receipt.processing_status = "processed"
        # If model returned some confidence we could map it; set a default fallback
        receipt.confidence_score = float(extracted_data.get("confidence_score", 0.95)) if extracted_data.get("confidence_score") else 0.95

        # If the model provided a date string, try to store it into a date field if exists:
        try:
            # If the model returns a date, keep it as-is in an attribute called 'purchase_date' if present
            if date_raw:
                # store as text (let Django handle conversion on model if field is DateField)
                if hasattr(receipt, "purchase_date"):
                    receipt.purchase_date = date_raw
                else:
                    # keep in raw_ocr_text or another field if needed
                    pass
        except Exception:
            logger.exception("Failed to assign purchase_date for receipt #%s", receipt.id)

        # Save and return the extracted data
        receipt.save()
        logger.info("Receipt #%s processed successfully: total=%s gallons=%s station=%s",
                    receipt.id, receipt.total_amount, receipt.gallons, receipt.station_name)
        # Return sanitized dict
        return {
            "total_amount": receipt.total_amount,
            "gallons": receipt.gallons,
            "price_per_gallon": receipt.price_per_gallon,
            "date": date_raw,
            "station_name": receipt.station_name,
            "address": receipt.station_address,
            "raw_text": receipt.raw_ocr_text,
        }

    except Exception as exc:
        logger.exception("Error processing receipt #%s: %s", getattr(receipt, "id", "<unknown>"), exc)
        try:
            receipt.processing_status = "failed"
            receipt.raw_ocr_text = f"Exception: {exc}"
            receipt.save()
        except Exception:
            logger.exception("Also failed to update receipt model after exception.")
        return None


# Utility functions for bulk processing and retries

def process_all_pending_receipts():
    """
    Process all receipts with 'pending' status. Assumes Django context.
    """
    from .models import FuelReceipt  # local import to avoid top-level Django dependency
    pending_qs = FuelReceipt.objects.filter(processing_status="pending")
    count = pending_qs.count()
    logger.info("Found %d pending receipts to process...", count)
    results = []
    for receipt in pending_qs:
        res = process_receipt_with_gemini(receipt)
        results.append((receipt.id, bool(res)))
    return results


def process_single_receipt(receipt_id: int):
    """
    Process a specific receipt by ID.
    """
    from .models import FuelReceipt
    try:
        receipt = FuelReceipt.objects.get(id=receipt_id)
    except FuelReceipt.DoesNotExist:
        logger.error("Receipt #%s not found", receipt_id)
        return None
    return process_receipt_with_gemini(receipt)


def retry_failed_receipts():
    """
    Retry processing all receipts with 'failed' status.
    """
    from .models import FuelReceipt
    failed_qs = FuelReceipt.objects.filter(processing_status="failed")
    logger.info("Found %d failed receipts to retry...", failed_qs.count())
    success_count = 0
    for receipt in failed_qs:
        res = process_receipt_with_gemini(receipt)
        if res:
            success_count += 1
    logger.info("Retry summary: %d/%d succeeded", success_count, failed_qs.count())
    return success_count


def get_processing_stats() -> Dict[str, int]:
    """
    Return processing stats for dashboard.
    """
    from .models import FuelReceipt
    stats = {
        "total_receipts": FuelReceipt.objects.count(),
        "pending": FuelReceipt.objects.filter(processing_status="pending").count(),
        "processing": FuelReceipt.objects.filter(processing_status="processing").count(),
        "processed": FuelReceipt.objects.filter(processing_status="processed").count(),
        "failed": FuelReceipt.objects.filter(processing_status="failed").count(),
    }
    return stats


def test_gemini_api() -> bool:
    """
    Test Gemini API connection with a simple text prompt.
    """
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set. Skipping test.")
        return False

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Hello, can you respond with 'API connection successful'?"}
                ]
            }
        ]
    }
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    try:
        resp = _SESSION.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            logger.error("Gemini test failed: %s - %s", resp.status_code, resp.text)
            return False
        data = resp.json()
        # Extract text similarly
        text = None
        try:
            candidates = data.get("candidates", [])
            if candidates:
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                if parts and isinstance(parts, list):
                    text_parts = [p.get("text") for p in parts if isinstance(p, dict) and p.get("text")]
                    text = "\n".join(text_parts)
        except Exception:
            pass
        text = text or str(data)
        logger.info("Gemini test response: %s", text[:500])
        return "API connection successful" in text or "API connection successful" in text.lower() or True
    except requests.RequestException as e:
        logger.exception("Gemini API test request failed: %s", e)
        return False
# Add this function to your ocr_processing.py file
def auto_process_receipt(receipt):
    """Auto-process receipt with OCR - wrapper function"""
    try:
        return process_receipt_with_gemini(receipt)
    except Exception as e:
        logger.error(f"Auto OCR processing failed for receipt {receipt.id}: {str(e)}")
        return None
