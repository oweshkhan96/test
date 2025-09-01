from celery import shared_task
from django.conf import settings
from .models import FuelReceipt
from .services import ReceiptOCRService
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def process_receipt_ocr(self, receipt_id):
    """Background task to process receipt OCR"""
    try:
        receipt = FuelReceipt.objects.get(id=receipt_id)
        receipt.processing_status = 'processing'
        receipt.save()
        
        # Process the receipt
        ocr_service = ReceiptOCRService()
        result = ocr_service.process_receipt(receipt.receipt_image.path)
        
        if result['success']:
            # Update receipt with extracted data
            structured_data = result['structured_data']
            
            receipt.raw_ocr_text = result['raw_text']
            receipt.ai_extracted_data = structured_data
            receipt.confidence_score = structured_data.get('confidence', 0.0)
            
            # Map structured data to model fields
            if structured_data.get('station_name'):
                receipt.station_name = structured_data['station_name']
            if structured_data.get('gallons'):
                receipt.gallons = structured_data['gallons']
            if structured_data.get('price_per_gallon'):
                receipt.price_per_gallon = structured_data['price_per_gallon']
            if structured_data.get('total_amount'):
                receipt.total_amount = structured_data['total_amount']
            if structured_data.get('fuel_type'):
                receipt.fuel_type = structured_data['fuel_type']
            if structured_data.get('address'):
                receipt.station_address = structured_data['address']
            
            # Set status based on confidence
            if receipt.confidence_score > 0.8:
                receipt.processing_status = 'processed'
            else:
                receipt.processing_status = 'manual_review'
                
            receipt.save()
            
            logger.info(f"Receipt {receipt_id} processed successfully with confidence {receipt.confidence_score}")
            return {'status': 'success', 'confidence': receipt.confidence_score}
            
        else:
            receipt.processing_status = 'failed'
            receipt.save()
            logger.error(f"Receipt {receipt_id} processing failed: {result.get('error')}")
            return {'status': 'failed', 'error': result.get('error')}
            
    except FuelReceipt.DoesNotExist:
        logger.error(f"Receipt {receipt_id} not found")
        return {'status': 'failed', 'error': 'Receipt not found'}
    except Exception as e:
        logger.error(f"Unexpected error processing receipt {receipt_id}: {str(e)}")
        return {'status': 'failed', 'error': str(e)}
