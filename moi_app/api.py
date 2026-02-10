import frappe
import os

@frappe.whitelist()
def send_email_from_field(**args):
    # frappe.msgprint(f'{args=}')
    # frappe.msgprint(f'{args.message=}')
    
    if not args['recipient']:
        frappe.throw("No email address found for the user.")
    email_attachments = args.get('email_attachments', None)
    subject = "رد من وزارة الإعلام"
    
    # Format attachments for frappe.sendmail
    attachments = []

    if email_attachments:
        # Ensure the file exists on the server
        file_path = os.path.join(frappe.get_site_path().strip('./'), email_attachments.lstrip('/'))

        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                attachments.append({
                    "fname": os.path.basename(file_path),
                    "fcontent": f.read(),
                })



    # try:
    frappe.sendmail(
        recipients=args['recipient'],
        subject=subject,
        message=args['message'],
        attachments=attachments,
        queue_separately=False
        )
    frappe.msgprint('email sent successfuly')
    # except Exception as e:
    #     frappe.throw(f"Failed to send confirmation email {e}")


# your_app/api.py or your_app/utils/ocr.py

import frappe
from frappe import _
import os
import re
import requests
from twocaptcha import TwoCaptcha

@frappe.whitelist()
def extract_text_from_image(file_url=None, file_id=None):
    """
    Extract Arabic text from an uploaded image using Tesseract OCR
    :param file_url: File URL (e.g., /files/image.jpg)
    :param file_id: Optional File document name
    :return: Extracted text
    """
    # Resolve file path
    if file_id:
        file_doc = frappe.get_doc("File", file_id)
        file_url = file_doc.file_url

    if not file_url:
        frappe.throw(_("No file specified"))

    # Get full file path
    if file_url.startswith("/files/"):
        file_path = frappe.get_site_path("public", file_url.lstrip("/"))
    else:
        file_path = frappe.get_site_path(file_url.lstrip("/"))

    if not os.path.exists(file_path):
        frappe.throw(_("File not found on server: {0}").format(file_path))

    api_key = '53f7ff6d8f4f00da16171cc59cbaf405'

    solver = TwoCaptcha(api_key)

    try:
        result = solver.recaptcha(
            sitekey='6LcVZBcUAAAAAA-RAZxClme__LbuwIRzkxUS5ggG',
            url='https://www.i2ocr.com/free-online-arabic-ocr'
        )

        print('CAPTCHA solved:', result['code'])


        url = "https://www.i2ocr.com/process_form"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0',
            'Referer': 'https://www.i2ocr.com/',
            'X-Requested-With': 'XMLHttpRequest',
        }

        with open(file_path, "rb") as img_file:
            files = {
                'i2ocr_languages': (None, 'eg,ara'),
                'engine_options': (None, 'engine_3'),
                'layout_options': (None, 'single_column'),
                'i2ocr_uploadedfile': ('image.jpg', img_file, 'image/jpeg'),
                'ocr_type': (None, '1'),
                'ly': (None, 'single_column'),
                'en': (None, '3'),
                'g-recaptcha-response': (None, result['code']),  # This may still block us if CAPTCHA required
            }

            response = requests.post(url, headers=headers, files=files)

            js_code = response.text

            # Extract the \uXXXX string from $("#ocrTextBox").val("...")
            match = re.search(r'\$\("#ocrTextBox"\)\.val\("([^"]+)"\)', js_code)
            if match:
                escaped_text = match.group(1)
                ocr_text = escaped_text.encode('utf-8').decode('unicode_escape')
                print(ocr_text)
            else:
                print("OCR text not found in response")

            return {
                "text": ocr_text,
                "message": _("Text extracted successfully"),
                "language": "Arabic (ara)"
            }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "OCR Extraction Failed")
        frappe.throw(_("Failed to extract text: {0}").format(str(e)))