from django.core.management.base import BaseCommand
from receipts.ocr_processing import process_all_pending_receipts, process_single_receipt

class Command(BaseCommand):
    help = 'Process receipt images with OCR'

    def add_arguments(self, parser):
        parser.add_argument(
            '--receipt-id',
            type=int,
            help='Process specific receipt by ID',
        )

    def handle(self, *args, **options):
        if options['receipt_id']:
            self.stdout.write(f"Processing receipt #{options['receipt_id']}...")
            result = process_single_receipt(options['receipt_id'])
            if result:
                self.stdout.write(self.style.SUCCESS(f'Successfully processed receipt #{options["receipt_id"]}'))
            else:
                self.stdout.write(self.style.ERROR(f'Failed to process receipt #{options["receipt_id"]}'))
        else:
            self.stdout.write('Processing all pending receipts...')
            process_all_pending_receipts()
            self.stdout.write(self.style.SUCCESS('Finished processing all pending receipts'))
