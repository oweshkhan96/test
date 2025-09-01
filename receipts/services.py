import ollama
import pytesseract
from PIL import Image
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReceiptOCRService:
    def __init__(self):
        # Updated for ollama-python 0.1.2
        self.client = ollama.Client(host='http://ollama:11434')
        
    def process_receipt(self, image_path):
        """Process receipt image using OCR + Llama 3.1"""
        try:
            # Step 1: Extract raw text with Tesseract
            raw_text = pytesseract.image_to_string(Image.open(image_path))
            logger.info(f"Raw OCR text length: {len(raw_text)}")
            
            # Step 2: Use Llama 3.1 to structure the data
            structured_data = self.extract_structured_data(raw_text)
            
            return {
                'success': True,
                'raw_text': raw_text,
                'structured_data': structured_data,
                'confidence': structured_data.get('confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'raw_text': '',
                'structured_data': {},
                'confidence': 0.0
            }
    
    def extract_structured_data(self, raw_text):
        """Use Llama 3.1 to extract structured data from OCR text"""
        prompt = f"""
You are an AI assistant specialized in extracting fuel receipt data. 
Analyze this fuel station receipt text and extract key information.

Receipt text:
{raw_text}

Extract the following information and return ONLY a valid JSON object:
{{
    "station_name": "station name if found",
    "transaction_date": "YYYY-MM-DD format if found",
    "transaction_time": "HH:MM format if found", 
    "fuel_type": "petrol/diesel/premium etc",
    "gallons": "number only, decimal format",
    "price_per_gallon": "price per gallon, decimal format",
    "total_amount": "total cost, decimal format",
    "address": "station address if available",
    "confidence": "confidence score 0.0-1.0 based on text clarity"
}}

If any field cannot be determined, use null for that field.
Return only the JSON object, no other text.
        """
        
        try:
            response = self.client.generate(
                model='llama3.1',
                prompt=prompt,
                stream=False
            )
            
            # Extract JSON from response
            response_text = response['response'].strip()
            
            # Try to parse JSON
            extracted_data = json.loads(response_text)
            
            # Validate and clean the data
            return self.validate_extracted_data(extracted_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Llama response as JSON: {e}")
            return self.fallback_extraction(raw_text)
        except Exception as e:
            logger.error(f"Llama processing failed: {e}")
            return self.fallback_extraction(raw_text)
    

    def validate_extracted_data(self, data):
        """Validate and clean extracted data"""
        cleaned = {}
        
        # Clean station name
        cleaned['station_name'] = str(data.get('station_name', '')).strip() if data.get('station_name') else ''
        
        # Parse and validate date
        if data.get('transaction_date'):
            try:
                cleaned['transaction_date'] = data['transaction_date']
            except:
                cleaned['transaction_date'] = None
        else:
            cleaned['transaction_date'] = None
            
        # Clean numeric fields
        for field in ['gallons', 'price_per_gallon', 'total_amount']:
            try:
                value = data.get(field)
                if value and str(value).replace('.', '').replace('-', '').isdigit():
                    cleaned[field] = float(value)
                else:
                    cleaned[field] = None
            except:
                cleaned[field] = None
        
        # Other fields
        cleaned['fuel_type'] = str(data.get('fuel_type', '')).strip().lower()
        cleaned['address'] = str(data.get('address', '')).strip()
        cleaned['confidence'] = min(max(float(data.get('confidence', 0.5)), 0.0), 1.0)
        
        return cleaned
    
    def fallback_extraction(self, raw_text):
        """Fallback method using basic pattern matching"""
        # Simple regex-based extraction as fallback
        import re
        
        data = {
            'station_name': '',
            'transaction_date': None,
            'fuel_type': '',
            'gallons': None,
            'price_per_gallon': None,
            'total_amount': None,
            'address': '',
            'confidence': 0.3  # Lower confidence for fallback
        }
        
        # Basic pattern matching
        amount_pattern = r'\$?(\d+\.\d{2})'
        gallon_pattern = r'(\d+\.\d{1,3})\s*GAL'
        
        amounts = re.findall(amount_pattern, raw_text)
        gallons = re.findall(gallon_pattern, raw_text, re.IGNORECASE)
        
        if amounts:
            data['total_amount'] = float(amounts[-1])  # Usually last amount is total
        if gallons:
            data['gallons'] = float(gallons[0])
            
        return data
