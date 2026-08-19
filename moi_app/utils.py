import pyqrcode
import io
import base64
import re
import os
from frappe.utils.file_manager import save_file
from urllib.parse import urlparse
import frappe
from frappe.utils.pdf import get_pdf
from pypdf import PdfReader, PdfWriter

from bs4 import BeautifulSoup

def generate_item_qr(doc, method):
    if not doc.custom_origin_number:
        return

    # Generate QR code content
    qr_content = doc.custom_origin_number
    qr = pyqrcode.create(qr_content, encoding='utf-8')

    # Use BytesIO to hold binary PNG data
    buffer = io.BytesIO()
    qr.png(buffer, scale=5)  # Writes binary PNG into buffer
    buffer.seek(0)  # Reset pointer to beginning

    # Get raw binary (bytes), NOT base64
    file_content = buffer.getvalue()  # ← This is correct: raw PNG bytes
    # Save file using Frappe's save_file
    file_doc = save_file(
        fname=f"{doc.custom_origin_number}_qr.png".replace('/', '-'),
        content=file_content,       # ✅ Raw bytes, not base64
        dt="Asset",                 # DocType
        dn=doc.name,                # Document name
        is_private=1                # Private file
    )

    # Set the URL in the custom field
    doc.custom_qr_code = file_doc.file_url

    # Close buffer (good practice)
    buffer.close()
    
    
# def redirect_after_login(login_manager=None):
#     user = frappe.session.user

#     # user_doc = frappe.get_doc("User", user)
#     # user_type = user_doc.user_type
#     # # Example: Redirect Employee to their own Employee record
#     # if user_type == "System User":
#     #     frappe.local.response["type"] = "redirect"
#     #     frappe.local.response["location"] = f"/desk"
#     #     return

#     # Fallback: Go to desktop
#     frappe.local.response["type"] = "redirect"
#     frappe.local.response["location"] = "/platform"

def to_eastern_arabic_numerals(n):
    western = '0123456789'
    eastern = '٠١٢٣٤٥٦٧٨٩'
    s = str(n)
    return s.translate(str.maketrans(western, eastern))

import asyncio
from playwright.async_api import async_playwright

async def _html_to_pdf_bytes(html_content):
    """
    Convert HTML to PDF bytes using Playwright with large content handling.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-sandbox',
                '--disable-software-rasterizer'
            ]
        )
        
        page = await browser.new_page()
        
        try:
            # Write HTML directly using evaluate
            await page.evaluate("""
                (html) => {
                    document.open();
                    document.write(html);
                    document.close();
                }
            """, html_content)
            
            # Wait for any dynamic content
            await page.wait_for_timeout(1000)
            
            # Generate PDF
            pdf_data = await page.pdf(
                format='A4',
                print_background=True,
                prefer_css_page_size=True
            )
            
            return pdf_data
            
        except Exception as e:
            frappe.log_error(f"PDF Error: {str(e)}", "PDF Generation")
            raise
            
        finally:
            await browser.close()

def html_to_pdf(html_content: str) -> bytes:
    """
    Synchronous wrapper to convert HTML to PDF bytes.
    Returns raw PDF data for use with frappe.get_doc().
    """
    return asyncio.run(_html_to_pdf_bytes(html_content))


def embed_images_in_html(html_content):

    site_url = frappe.utils.get_url()  # e.g., "http://example.com" or "https://example.com"
    site_domain = urlparse(site_url).netloc.lower()

    def replace_img_tag(match):
        full_tag = match.group(0)
        src = match.group(1)

        file_path = None

        try:
            # Parse the src URL
            parsed = urlparse(src)
            path = parsed.path

            # Case 1: Relative path → /files/xxx.png or /private/files/xxx.png
            if src.startswith("/"):
                if src.startswith("/files/"):
                    relative_path = src[len("/files/"):]
                    file_path = frappe.get_site_path("public", "files", relative_path)
                elif src.startswith("/private/files/"):
                    relative_path = src[len("/private/files/"):]
                    file_path = frappe.get_site_path("private", "files", relative_path)

            # Case 2: Absolute URL on the same site → http://example.com/files/xxx.png
            elif parsed.scheme in ("http", "https") and parsed.netloc.lower() == site_domain:
                if path.startswith("/files/"):
                    relative_path = path[len("/files/"):]
                    file_path = frappe.get_site_path("public", "files", relative_path)
                elif path.startswith("/private/files/"):
                    relative_path = path[len("/private/files/"):]
                    file_path = frappe.get_site_path("private", "files", relative_path)

            # Skip if not matched (external, data:, blob:, etc.)
            if not file_path:
                return full_tag

            # Check if file exists
            if not os.path.isfile(file_path):
                frappe.log_warning(f"Image not found: {file_path} (src='{src}')")
                return full_tag

            # Detect MIME type
            ext = os.path.splitext(file_path)[1].lower()
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".svg": "image/svg+xml",
                ".webp": "image/webp"
            }.get(ext, "image/png")

            # Read and encode
            with open(file_path, "rb") as f:
                data = f.read()
                b64 = base64.b64encode(data).decode("utf-8")
                data_uri = f"data:{mime};base64,{b64}"

            # Safely replace only the src value (preserve other attributes)
            new_tag = re.sub(
                r'(src\s*=\s*["\'])[^"\']*(["\'])',
                rf'\1{data_uri}\2',
                full_tag,
                count=1,
                flags=re.IGNORECASE
            )
            return new_tag

        except Exception as e:
            frappe.log_error(f"Failed to embed image {src}: {str(e)}")
            return full_tag

    # Regex to match <img ... src="URL" ...>
    # Captures both relative and absolute (http/https) URLs under /files/ or /private/files/
    # Supports .png, .jpg, .jpeg, .gif, .svg, .webp
    img_pattern = r'<img\b[^>]*src\s*=\s*["\']((https?://[^"\']*)?/(?:private/)?files/[^"\']+\.(?:png|jpg|jpeg|gif|svg|webp))["\'][^>]*>'

    updated_html = re.sub(img_pattern, replace_img_tag, html_content, flags=re.IGNORECASE)
    return updated_html

@frappe.whitelist()
def attach_pdf(doc, method):
    try:
        if type(doc) == dict:
            doc = frappe.get_doc(doc['doctype'], doc['name'])
        # ✅ Force weasyprint
        frappe.local.conf.pdf_generation_tool = "weasyprint"

        # 🔍 Get DEFAULT print format for this doctype
        print_format = frappe.db.get_value(
            "Property Setter",
            {
                "doc_type": doc.doctype,
                "property": "default_print_format"
            },
            "value"
        )
        # Fallback 1: Check DocType's default print format field
        if not print_format:
            print_format = frappe.db.get_value("DocType", doc.doctype, "default_print_format")
        
        # Fallback 2: Use "Standard" if none set
        if not print_format:
            print_format = "Standard"
            frappe.log_warning(f"No default print format found for {doc.doctype}. Using 'Standard'.")
        
        # Generate HTML
        html = frappe.get_print(
            doc.doctype,
            doc.name,
            print_format=print_format,
        )

        # Fix absolute URLs & embed images
        site_url = frappe.utils.get_url().rstrip("/")
        html = html.replace('src="/', f'src="{site_url}/') \
                   .replace('href="/', f'href="{site_url}/')
        html = embed_images_in_html(html)

        # Generate PDF
        # pdf_data = frappe.utils.pdf.get_pdf(html)
        pdf_data = html_to_pdf(html)

        # Delete only the previous "_Approved.pdf" file(s)
        pattern = "%_Approved.pdf"
        existing_approved_files = frappe.get_all("File", filters={
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "file_name": ("like", pattern),
            "is_private": 1
        }, pluck="name")

        for file_name in existing_approved_files:
            frappe.delete_doc("File", file_name, ignore_permissions=True)
        
        # Attach file
        file_name = f"{doc.name}_Approved.pdf"
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": file_name,
            "attached_to_doctype": doc.doctype,
            "attached_to_name": doc.name,
            "is_private": 1,
            "content": pdf_data
        })
        file_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        frappe.msgprint("✅  من الطلب PDF  تم إرفاق نسخة", alert=True, indicator="green")

    except Exception as e:
        frappe.log_error("PDF Attachment Error", str(e))
        frappe.throw(f"فشل إنشاء PDF: {str(e)}")


def number_to_arabic_words(amount, currency="USD"):
    """
    Convert a number to Arabic words with Syrian currency formatting.
    
    Args:
        amount (float/int): Number to convert (e.g., 123456.78)
        currency (str): "SYP" for Syrian Pounds (default), "USD" for Dollars
    
    Returns:
        str: Arabic words (e.g., "مائة وثلاثة وعشرون ألفًا وأربعمائة وستة وخمسون ليرة سورية وثمانية وسبعون فلسًا")
    """
    # Arabic digits mapping
    ONES = [
        "", "واحد", "اثنان", "ثلاثة", "أربعة", "خمسة", "ستة", 
        "سبعة", "ثمانية", "تسعة", "عشرة", "أحد عشر", "اثنا عشر",
        "ثلاثة عشر", "أربعة عشر", "خمسة عشر", "ستة عشر", 
        "سبعة عشر", "ثمانية عشر", "تسعة عشر"
    ]
    
    TENS = [
        "", "", "عشرون", "ثلاثون", "أربعون", "خمسون", 
        "ستون", "سبعون", "ثمانون", "تسعون"
    ]
    
    HUNDREDS = [
        "", "مائة", "مائتان", "ثلاثمائة", "أربعمائة", "خمسمائة",
        "ستمائة", "سبعمائة", "ثمانمائة", "تسعمائة"
    ]
    
    # Scale words (feminine for numbers, masculine for currency)
    SCALES = [
        "", 
        "ألف",      # 10^3
        "مليون",    # 10^6
        "مليار",    # 10^9
        "تريليون"  # 10^12
    ]

    def _convert_integer(n):
        """Convert integer part (0 to 999,999,999,999) to Arabic words"""
        if n == 0:
            return "صفر"
        
        parts = []
        scale_idx = 0
        
        while n > 0:
            chunk = n % 1000
            n //= 1000
            
            if chunk != 0:
                chunk_words = _convert_hundreds(chunk)
                if scale_idx > 0:
                    # Handle إعراب for scale words
                    if chunk == 1:
                        # واحد ألف → ألف
                        scale_word = SCALES[scale_idx]
                    elif chunk == 2:
                        # اثنان ألف → ألفان
                        scale_word = SCALES[scale_idx] + "ان"
                    elif 3 <= chunk <= 10:
                        # ثلاثة آلاف, عشرة آلاف
                        scale_word = SCALES[scale_idx] + " آلاف"
                    else:
                        # واحد وعشرون ألفًا
                        scale_word = SCALES[scale_idx] + "ًا"
                    chunk_words += " " + scale_word
                parts.append(chunk_words)
            scale_idx += 1
        
        return " و ".join(reversed(parts))

    def _convert_hundreds(n):
        """Convert 0-999 to words"""
        if n == 0:
            return ""
        
        words = []
        hundreds = n // 100
        remainder = n % 100
        
        if hundreds > 0:
            words.append(HUNDREDS[hundreds])
        
        if remainder > 0:
            if remainder < 20:
                words.append(ONES[remainder])
            else:
                ones = remainder % 10
                tens = remainder // 10
                if ones == 0:
                    words.append(TENS[tens])
                elif ones == 1:
                    # واحد وعشرون
                    words.append("واحد و" + TENS[tens])
                elif ones == 2:
                    # اثنان وثلاثون
                    words.append("اثنان و" + TENS[tens])
                else:
                    # ثلاثة وثلاثون
                    words.append(ONES[ones] + " و" + TENS[tens])
        
        return " و ".join(words)

    def _format_currency(integer_part, decimal_part):
        """Format with Syrian currency units"""
        # Integer part: ليرة / ليرات
        if currency.upper() == "USD":
            int_unit_singular = "دولار أمريكي"
            int_unit_dual = "دولاران أمريكيان"
            int_unit_plural = "دولارات أمريكية"
            dec_unit_singular = "سنت"
            dec_unit_dual = "سنتان"
            dec_unit_plural = "سنتات"
        else:  # SYP
            int_unit_singular = "ليرة سورية"
            int_unit_dual = "ليرتان سوريتان"
            int_unit_plural = "ليرات سورية"
            dec_unit_singular = "فلس"
            dec_unit_dual = "فلسان"
            dec_unit_plural = "فلسات"

        result = []

        # Integer part
        if integer_part == 0 and decimal_part == 0:
            return "صفر " + int_unit_plural
        
        if integer_part > 0:
            int_words = _convert_integer(integer_part)
            if integer_part == 1:
                result.append(int_words + " " + int_unit_singular)
            elif integer_part == 2:
                result.append(int_words + " " + int_unit_dual)
            elif 3 <= integer_part <= 10:
                result.append(int_words + " " + int_unit_plural)
            else:
                # واحد وعشرون ليرةً سوريةً → but colloquially: ليرة سورية
                result.append(int_words + " " + int_unit_singular)

        # Decimal part
        if decimal_part > 0:
            if integer_part > 0:
                result.append("و")
            
            dec_words = _convert_integer(decimal_part)
            if decimal_part == 1:
                result.append(dec_words + " " + dec_unit_singular)
            elif decimal_part == 2:
                result.append(dec_words + " " + dec_unit_dual)
            elif 3 <= decimal_part <= 10:
                result.append(dec_words + " " + dec_unit_plural)
            else:
                result.append(dec_words + " " + dec_unit_singular)
        
        return " ".join(result)

    # Main logic
    try:
        # Handle negative
        is_negative = amount < 0
        amount = abs(float(amount))
        
        integer_part = int(amount)
        decimal_part = int(round((amount - integer_part) * 100))
        
        # Fix floating-point errors
        if decimal_part >= 100:
            integer_part += 1
            decimal_part -= 100
        
        words = _format_currency(integer_part, decimal_part)
        
        if is_negative:
            words = "سالب " + words
        
        return words.strip()
    
    except Exception as e:
        # Fallback for errors
        return f"خطأ في التحويل: {str(e)}"
    


def get_employee_assets(employee):
    from bs4 import BeautifulSoup
    # Get summarized assets: each item with total quantity
    assets_summary = frappe.db.sql(r"""
        SELECT 
            item_code,
            item_name,
            custom_origin_number AS assets_origin_number,
            custom_description AS assets_description,
            custom_color AS color,
            custom_extensions AS extensions,
            asset_quantity,
            custom_model AS model,
            asset_category AS item_type
        FROM 
            `tabAsset`
        WHERE 
            custodian = %(employee)s
            AND status NOT IN ('Scrapped', 'Disposed', 'Sold')
        ORDER BY assets_origin_number

    """, {"employee": employee}, as_dict=True)
    for row in assets_summary:
        # if row.get('assets_origin_number'):
        #     row['assets_origin_number'] = row['assets_origin_number'].replace('\n', '<br>')

        desc = row.get('assets_description', '')

        soup = BeautifulSoup(desc, 'html.parser')
        # if row['item_name'] == 'براد مكتبي':
        #     breakpoint()
        # if any(k in row.get('item_name', '') for k in ['لابتوب', 'شاشة', 'حاسب', 'حاسوب','موبايل']) or row['item_type']=='اليات' or row['item_type']=='اليات':
        row['item_name_with_manufacturer'] = row['item_name']
        row['manufacturer'] = ''

        if row['item_type']!='أسلحة و معدات حماية' and desc:
            for td in soup.find_all('td'):
                if td.get_text(strip=True) == 'الشركة المصنعة':
                    # Get the previous sibling td (the one before this td)
                    prev_td = td.find_previous_sibling('td')
                    if prev_td:
                        manufacturer = prev_td.get_text(strip=True)
                        row['manufacturer'] = manufacturer
                        row['item_name_with_manufacturer'] = f"{row['item_name']} \n {manufacturer}"

        keep_keys = ['الشركة المصنعة','نوع المعالج', 'حجم الرامات', 'مواصفات الهارد', 'ملحقات',
                     'القياس','سنة الصنع','نوع الوقود', "بلد المنشا",'عيار الذخيرة','عدد المخازن','الملحقات']

        # Find all rows and collect those to KEEP (NOT remove)
        tables = soup.find_all('table')
        quantity_found = False
        if tables:
            table = tables[0]
            rows = table.find_all('tr')
            
            rows_to_keep = []
            for table_row in rows:
                cells = table_row.find_all('td')
                if len(cells) >= 2:
                    key_cell = cells[1] if len(cells) > 1 else None
                    if key_cell:
                        key_text = key_cell.get_text(strip=True)
                        if 'العدد' == key_text.strip():
                            quantity_found = True
                            row['total_quantity'] = cells[0].get_text(strip=True)
                        if key_text in keep_keys:
                            rows_to_keep.append(table_row)
                else:
                    rows_to_keep.append(table_row)
            if not quantity_found:
                row['total_quantity'] = row['asset_quantity']
            # Create a new table with kept rows
            if rows_to_keep:
                # Create new table with same attributes
                new_table = BeautifulSoup('<table></table>', 'html.parser').table
                if table.attrs:
                    for attr, value in table.attrs.items():
                        new_table[attr] = value
                
                # Add kept rows
                for table_row in rows_to_keep:
                    new_table.append(table_row)
            
                row['assets_description'] = str(new_table)

    assets_summary = sorted(assets_summary, key=lambda x: x.get('assets_description', ''),reverse=True)
    return assets_summary

def get_asset_description_by_id(asset_id):
    """
    Get asset description with only specified fields
    """
    from bs4 import BeautifulSoup
    
    asset = frappe.db.sql(r"""
        SELECT 
            custom_origin_number AS assets_origin_number,
            custom_description AS assets_description,
            custom_color AS color,
            custom_extensions AS extensions,
            asset_quantity,
            custom_model AS model,
            asset_category AS item_type
        FROM 
            `tabAsset`
        WHERE 
            name = %(asset_id)s
            AND status NOT IN ('Scrapped', 'Disposed', 'Sold')
    """, {"asset_id": asset_id}, as_dict=True)
    
    if not asset:
        return None
    
    asset = asset[0]
    desc = asset.get('assets_description', '')
    soup = BeautifulSoup(desc, 'html.parser')
    
    # Define keys to keep
    keep_keys = [
        'الشركة المصنعة', 'نوع المعالج', 'حجم الرامات', 'مواصفات الهارد', 'ملحقات',
        'القياس', 'سنة الصنع', 'نوع الوقود', 'بلد المنشا', 'عيار الذخيرة', 
        'عدد المخازن', 'الملحقات'
    ]
    
    # Start building HTML
    html = '''
    <div style="direction: rtl; text-align: right;">
        <table class="table table-bordered">
            <tbody>
    '''
    
    # Add basic fields
    basic_data = [
        ('رقم المنشأ', asset.get('assets_origin_number', '')),
        ('اللون', asset.get('color', '')),
        ('الملحقات', asset.get('extensions', '')),
        ('الموديل', asset.get('model', '')),
        ('العدد', str(asset.get('asset_quantity', '')))
    ]
    
    for key, value in basic_data:
        if value:
            html += f'''
                <tr>
                    <td style="text-align: right; font-weight: bold;">{key}</td>
                    <td style="text-align: right;">{value}</td>
                </tr>
            '''
    
    # Add filtered description fields
    if desc:
        desc_table = soup.find('table')
        if desc_table:
            rows = desc_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    key = cells[1].get_text(strip=True) if cells[1] else ''
                    value = cells[0].get_text(strip=True) if cells[0] else ''
                    
                    if key and value and key in keep_keys:
                        html += f'''
                <tr>
                    <td style="text-align: right; font-weight: bold;">{key}</td>
                    <td style="text-align: right;">{value}</td>
                </tr>
                        '''
    
    # Close HTML
    html += '''
            </tbody>
        </table>
    </div>
    '''
    
    return html
@frappe.whitelist()
def fetch_asset_description_by_id(asset_id):
    """
    API endpoint to fetch asset details
    Called from client-side script
    """
    if not asset_id:
        return []
    
    try:
        details = get_asset_description_by_id(asset_id)
        return details
    except Exception as e:
        frappe.log_error(f"Error fetching details for {asset_id}: {str(e)}")
        frappe.throw("Failed to fetch details: {0}").format(str(e))

@frappe.whitelist()
def fetch_employee_assets(employee):
    """
    API endpoint to fetch assets for an employee
    Called from client-side script
    """
    if not employee:
        return []
    
    try:
        assets = get_employee_assets(employee)
        return assets
    except Exception as e:
        frappe.log_error(f"Error fetching assets for {employee}: {str(e)}")
        frappe.throw("Failed to fetch assets: {0}").format(str(e))
        
from datetime import datetime
from hijridate import Gregorian

def gregorian_to_hijri(date_str):
    if isinstance(date_str, str):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    else:
        date_obj = date_str

    gregorian_str = str(date_obj).split(" ")[0]
    hijri_date = Gregorian.fromdate(date_obj).to_hijri()
    
    return hijri_date, gregorian_str

@frappe.whitelist()
def get_hijri_date(date_str):
    """API endpoint for client-side calls"""
    hijri, gregorian = gregorian_to_hijri(date_str)
    return {"hijri": hijri, "gregorian": gregorian}

@frappe.whitelist()
def convert_table(date_str):
    """API endpoint for client-side calls"""
    text = convert_table_to_text(date_str)
    return { "text": text}


import frappe

@frappe.whitelist()
def get_department_head_approver(employee):
    """
    Traverse reporting chain upwards to find first user with 'Head of Department' role.
    First checks if the applicant themselves has the role.
    Returns: {'user_id': 'user@domain.com'} or {'error': 'message'}
    """
    # Treat empty, null-like or explicit "None"/"null" strings as missing
    if not employee or str(employee).strip().lower() in ("none", "null", ""):
        return {"error": _("No employee specified")}
    
    # Validate employee exists
    if not frappe.db.exists("Employee", employee):
        return {"error": _("Employee {0} not found").format(employee)}
    
    # STEP 1: Check if the applicant themselves has "Head of Department" role
    applicant_user = frappe.db.get_value("Employee", employee, "user_id")
    if applicant_user:
        if frappe.db.exists("User", applicant_user):
            try:
                if "Head of Department" in frappe.get_roles(applicant_user):
                    # Verify this user is actually the department head
                    applicant_dept = frappe.db.get_value("Employee", employee, "department")
                    if applicant_dept:
                        dept_head = frappe.db.get_value("Department", applicant_dept, "department_head")
                        if dept_head == applicant_user:
                            return {
                                "user_id": applicant_user,
                                "level": 0,
                                "verified": True,
                                "source": "applicant_is_department_head"
                            }
                    # If department_head field doesn't match but user has role
                    return {
                        "user_id": applicant_user,
                        "level": 0,
                        "verified": False,
                        "source": "applicant_has_head_role"
                    }
            except Exception as e:
                frappe.log_error(
                    f"Error checking roles for applicant {applicant_user}: {str(e)}",
                    "get_department_head_approver"
                )
    
    # STEP 2: Traverse reporting chain to find Head of Department
    current_emp = employee
    max_depth = 10  # Prevent infinite loops in circular reporting structures
    visited = set()  # Detect circular references
    depth = 0
    
    for depth in range(max_depth):
        # Prevent circular reference loops
        if current_emp in visited:
            frappe.log_error(
                f"Circular reporting chain detected at employee {current_emp}",
                "get_department_head_approver"
            )
            return {"error": _("Circular reporting structure detected. Contact HR.")}
        visited.add(current_emp)
        
        # Get immediate manager
        manager_emp = frappe.db.get_value("Employee", current_emp, "reports_to")
        if not manager_emp:
            break
        
        # Get manager's linked user
        manager_user = frappe.db.get_value("Employee", manager_emp, "user_id")
        if not manager_user:
            # Skip to next level if manager has no user account
            current_emp = manager_emp
            continue
        
        # CRITICAL: Verify user exists before checking roles
        if not frappe.db.exists("User", manager_user):
            frappe.log_error(
                f"User {manager_user} linked to employee {manager_emp} does not exist",
                "get_department_head_approver"
            )
            current_emp = manager_emp
            continue
        
        # Check for Head of Department role (exact match)
        try:
            if "Head of Department" in frappe.get_roles(manager_user):
                # Optional: Verify this user is actually head of applicant's department
                applicant_dept = frappe.db.get_value("Employee", employee, "department")
                if applicant_dept:
                    dept_head = frappe.db.get_value("Department", applicant_dept, "department_head")
                    if dept_head == manager_user:
                        return {
                            "user_id": manager_user,
                            "level": depth + 1,
                            "verified": True,
                            "source": "reporting_chain_verified"
                        }
                
                # Fallback: Return found user even if not department_head field (role-based match)
                return {
                    "user_id": manager_user,
                    "level": depth + 1,
                    "verified": False,
                    "source": "reporting_chain_role_match"
                }
        except Exception as e:
            frappe.log_error(
                f"Error checking roles for {manager_user}: {str(e)}",
                "get_department_head_approver"
            )
        
        # Move up the chain
        current_emp = manager_emp
    
    # STEP 3: Final fallback - Try direct department head lookup
    applicant_dept = frappe.db.get_value("Employee", employee, "department")
    if applicant_dept:
        dept_head_user = frappe.db.get_value("Department", applicant_dept, "department_head")
        if dept_head_user and frappe.db.exists("User", dept_head_user):
            # Check if this user has the Head of Department role
            try:
                if "Head of Department" in frappe.get_roles(dept_head_user):
                    return {
                        "user_id": dept_head_user,
                        "level": "direct",
                        "verified": True,
                        "source": "department_head_field_with_role"
                    }
                else:
                    # User is set as department head but doesn't have the role
                    return {
                        "user_id": dept_head_user,
                        "level": "direct",
                        "verified": False,
                        "source": "department_head_field_no_role",
                        "warning": "User does not have 'Head of Department' role"
                    }
            except Exception as e:
                frappe.log_error(
                    f"Error checking roles for department head {dept_head_user}: {str(e)}",
                    "get_department_head_approver"
                )
    
    return {
        "error": "No approver with 'Head of Department' role found in reporting chain (max depth: {0})".format(max_depth),
        "chain_depth": depth + 1,
        "applicant_has_role": applicant_user and "Head of Department" in frappe.get_roles(applicant_user) if applicant_user and frappe.db.exists("User", applicant_user) else False
    }
    
    
import re
from bs4 import BeautifulSoup

def convert_table_to_text(html_content):
    """
    Convert HTML table to plain text format
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table')
    
    if not table:
        return html_content
    
    # Extract all text from table cells
    rows = table.find_all('tr')
    text_output = []
    
    for row in rows:
        cells = row.find_all('td')
        row_text = []
        for cell in cells:
            # Get text from cell and strip whitespace
            cell_text = cell.get_text(strip=True)
            if cell_text:
                row_text.append(cell_text)
        
        if row_text:
            text_output.append(' : '.join(row_text))
    
    return '<br>'.join(text_output)

"""Workflow progress bar — server side.

Exposes a workflow as a *graph* (states + transitions) rather than a single
flattened path, so the client can render branches, merges and rejection loops
for any DocType that has an active Workflow.
"""

import ast
import json
import re

import frappe
from frappe.model.workflow import get_workflow_name, is_transition_condition_satisfied
from frappe.utils import cint

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@frappe.whitelist()
def get_workflow_doctypes():
    """Every DocType that currently has an active Workflow.

    The client binds a form handler to each of these, so the progress bar works
    on any workflow-enabled DocType without being hard-coded to one.
    """
    doctypes = frappe.get_all(
        "Workflow",
        filters={"is_active": 1},
        pluck="document_type",
    )
    # A DocType can legitimately have more than one Workflow row; only one is
    # active at a time, but de-duplicate defensively.
    return sorted({dt for dt in doctypes if dt})


def boot_workflow_doctypes(bootinfo):
    """Ship the workflow DocType list in boot.

    Wire this up in hooks.py so the client binds its form handlers before any
    form renders, instead of racing the form load with an extra round trip::

        extend_bootinfo = "moi_app.utils.boot_workflow_doctypes"
    """
    bootinfo.workflow_doctypes = get_workflow_doctypes()


@frappe.whitelist()
def get_workflow_graph(doctype, docname=None, only_relevant=1):
    """Return the workflow graph for `doctype`, as it applies to one document.

    Keeps every state and every transition, so branching ("Approve" vs
    "Reject"), merges and loop-backs all survive to the client. Layout is the
    client's job; this is pure data.

    With `only_relevant` (the default) the graph is pruned to the paths that
    can actually apply to `docname`: transitions whose condition is false for
    this record are dropped, along with any state that becomes unreachable as a
    result. Pass ``only_relevant=0`` to get the full workflow definition.

    Returns None when the DocType has no active workflow.
    """
    only_relevant = cint(only_relevant)
    workflow_name = get_workflow_name(doctype)
    if not workflow_name:
        return None

    workflow = frappe.get_cached_doc("Workflow", workflow_name)
    state_field = workflow.workflow_state_field or "workflow_state"

    doc = None
    current_state = None
    if docname:
        doc = frappe.get_doc(doctype, docname)
        # Reading a document's workflow implies reading the document.
        doc.check_permission("read")
        current_state = doc.get(state_field)

    # `style` lives on the Workflow State master, not on the child row, so it is
    # fetched separately — one query for the whole workflow.
    styles = _state_styles([row.state for row in workflow.states])

    states = [
        {
            "name": row.state,
            "doc_status": cint(row.doc_status),
            "style": styles.get(row.state, ""),
            "allow_edit": row.allow_edit,
            "order": idx,
        }
        for idx, row in enumerate(workflow.states)
    ]

    known_states = {row["name"] for row in states}

    transitions = []
    for row in workflow.transitions:
        # A transition can reference a state that was removed from the States
        # table; skip it rather than emitting a dangling edge.
        if row.state not in known_states or row.next_state not in known_states:
            continue
        transitions.append(
            {
                "from_state": row.state,
                "to_state": row.next_state,
                "action": row.action,
                "allowed": row.allowed,
                "condition": row.condition or "",
                # "available to act on right now" vs "on this record's path"
                "satisfied": _condition_satisfied(row, doc),
                "applies": _condition_applies(row, doc, state_field),
            }
        )

    history = _state_history(
        doctype, docname, state_field, states, current_state, transitions
    )
    _mark_traversed(transitions, history, current_state)

    pruned = False
    if docname and only_relevant:
        states, transitions = _prune_to_relevant(
            states, transitions, current_state, history
        )
        pruned = True

    _annotate_phases(states, transitions, current_state, history)
    states = [st for st in states if st["phase"] != "other"]
    return {
        "workflow": workflow_name,
        "doctype": doctype,
        "docname": docname,
        "state_field": state_field,
        "current_state": current_state,
        "states": states,
        "transitions": transitions,
        "history": history,
        "pruned": pruned,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state_styles(state_names):
    """Map each Workflow State name to its `style` (Success, Danger, Warning...).

    The style is the workflow designer's own colour intent, which the client
    uses in preference to guessing from the state's name. It is stored on the
    Workflow State master — the `states` child rows do not carry it.
    """
    names = [name for name in set(state_names) if name]
    if not names:
        return {}

    rows = frappe.get_all(
        "Workflow State",
        filters={"name": ("in", names)},
        fields=["name", "style"],
    )
    return {row.name: row.style or "" for row in rows}


# Text that makes a comparison about *who is acting* rather than about the
# record. Such a comparison is false for every step the document has not
# reached yet, so it says nothing about whether that step is on the path.
_SESSION_MARKERS = ("frappe.session", "session.user", "frappe.user")


def _mentions_session(node):
    """Whether an expression node refers to the acting user."""
    try:
        text = ast.unparse(node).lower()
    except Exception:
        return False
    return any(marker in text for marker in _SESSION_MARKERS)


def _is_neutralised(node):
    """Whether a node has already been reduced to the neutral ``True``."""
    return isinstance(node, ast.Constant) and node.value is True


class _NeutraliseSession(ast.NodeTransformer):
    """Take the session-user test out of a condition, leaving the rest intact.

    A session comparison is *dropped from* the boolean expression rather than
    replaced by ``True`` inside it. Substituting the constant would make an
    ``or`` short-circuit — ``doc.total > 50000 or doc.approver ==
    frappe.session.user`` would become ``... or True`` and never test the
    record at all. Removing the clause leaves ``doc.total > 50000``, so the
    record still decides in both ``and`` and ``or`` expressions.
    """

    def __init__(self):
        self.changed = False

    def visit_Compare(self, node):
        if _mentions_session(node):
            self.changed = True
            return ast.copy_location(ast.Constant(value=True), node)
        return self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Children first, so session comparisons are already neutralised.
        self.generic_visit(node)

        kept = [value for value in node.values if not _is_neutralised(value)]
        if not kept:
            # Nothing but session tests — the whole clause is neutral.
            return ast.copy_location(ast.Constant(value=True), node)
        if len(kept) == 1:
            return kept[0]

        node.values = kept
        return node

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        # `not <session test>` must stay neutral rather than flip to False.
        if isinstance(node.op, ast.Not) and _is_neutralised(node.operand):
            return ast.copy_location(ast.Constant(value=True), node)
        return node


def _neutralise_session(condition):
    """Rewrite `condition` with the session-user test removed.

    The remaining record-data expression decides whether the branch belongs on
    this record's path::

        doc.total > 5 and doc.approver == frappe.session.user  ->  doc.total > 5
        doc.total > 5 or  doc.approver == frappe.session.user  ->  doc.total > 5
        doc.approver == frappe.session.user                    ->  True

    Note the ``or`` case: the clause is dropped, not replaced by ``True``, so
    the record half is still tested instead of being short-circuited away.

    Returns ``(rewritten, changed)``. On a malformed expression the original
    string is returned unchanged.
    """
    if not condition:
        return condition, False
    try:
        tree = ast.parse(condition.strip(), mode="eval")
    except SyntaxError:
        return condition, False

    transformer = _NeutraliseSession()
    tree = transformer.visit(tree)
    if not transformer.changed:
        return condition, False

    ast.fix_missing_locations(tree)
    try:
        return ast.unparse(tree), True
    except Exception:
        return condition, False


def _condition_applies(transition, doc, state_field):
    """Whether this branch belongs on the record's path.

    Distinct from :func:`_condition_satisfied`, which answers "is this action
    available right now". Here every session-user comparison is taken as true
    and the remainder of the expression is evaluated, so:

    * ``doc.grand_total > 50000`` — decided by the record; prunes when false.
    * ``doc.approver == frappe.session.user`` — becomes ``True``; always kept,
      otherwise the path would stop at the current state.
    * ``doc.total > 5 and doc.approver == frappe.session.user`` — becomes
      ``doc.total > 5``; the record still decides.

    A condition referring to the workflow state field describes *where* the
    document is rather than which way it goes, so it never prunes.
    """
    condition = transition.condition
    if not condition:
        return True
    if state_field and state_field.lower() in condition.lower():
        return True

    rewritten, changed = _neutralise_session(condition)
    if not changed:
        # No session reference — the plain evaluation already answers this.
        return _condition_satisfied(transition, doc)

    return _condition_satisfied(frappe._dict(condition=rewritten), doc)


def _reachable(transitions, origin, reverse=False):
    """States reachable from `origin`, following edges forwards or backwards.

    Returns a set that always contains `origin` itself, or an empty set when
    `origin` is falsy.
    """
    if not origin:
        return set()

    adjacency = {}
    for transition in transitions:
        source, target = transition["from_state"], transition["to_state"]
        if reverse:
            source, target = target, source
        adjacency.setdefault(source, []).append(target)

    seen = {origin}
    queue = [origin]
    while queue:
        node = queue.pop(0)
        for nxt in adjacency.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


def _annotate_phases(states, transitions, current_state, history):
    """Tag each state as past / current / future, so the client need not guess.

    Derived from the graph rather than from Version history, which is missing
    entirely on DocTypes that do not track changes.
    """
    ahead = _reachable(transitions, current_state) - {current_state}
    behind = _reachable(transitions, current_state, reverse=True) - {current_state}

    for state in states:
        name = state["name"]
        if name == current_state:
            state["phase"] = "current"
        elif name in history:
            state["phase"] = "past"
        elif name in ahead:
            # In a loop a state can sit on both sides; "still to come" is the
            # safer read than claiming it is already done.
            state["phase"] = "future"
        elif name in behind:
            state["phase"] = "past"
        else:
            state["phase"] = "other"


def _mark_traversed(transitions, history, current_state):
    """Flag the edges this document actually moved along.

    A traversed edge is kept even when its condition no longer holds: once a
    document leaves Draft the condition that let it leave is often false, and
    erasing that edge would erase the path the record genuinely took.
    """
    for transition in transitions:
        source = history.get(transition["from_state"])
        target_seen = (
            transition["to_state"] in history or transition["to_state"] == current_state
        )
        transition["traversed"] = bool(source is not None and target_seen)


def _prune_to_relevant(states, transitions, current_state, history):
    """Reduce the graph to the paths that can apply to this document.

    Kept:
      * every state the document has already been through,
      * the state it sits on now,
      * everything still reachable from there through transitions whose
        conditions currently hold.

    Dropped: branches gated behind a condition that is false for this record —
    e.g. a "grand_total > 50000" approval path on a 5,000 document — and any
    state left stranded once those edges go.

    Pruning uses `applies` (see :func:`_condition_applies`), not `satisfied`:
    session-user comparisons count as true so the rest of the expression
    decides. A branch gated purely on who is acting is therefore always kept —
    otherwise the graph would stop at the current state rather than showing the
    rest of the path.
    """
    # Drop an edge only when the record's own data rules it out.
    live = [t for t in transitions if t.get("traversed") or t.get("applies")]

    # Never strand the document. If every way out of the current state was
    # pruned, keep them: a path that dead-ends where the record happens to sit
    # is worse than showing a branch that may not apply.
    if current_state:
        exits = [t for t in transitions if t["from_state"] == current_state]
        if exits and not [t for t in live if t["from_state"] == current_state]:
            live = live + exits

    relevant = set(history)
    if current_state:
        relevant.add(current_state)

    # Ahead: walk forward from wherever the document sits (or the opening
    # state, for a record that has not entered the workflow yet).
    origin = current_state or (states[0]["name"] if states else None)
    relevant |= _reachable(live, origin)

    # Behind: walk backwards from the current state. Without this the middle of
    # the path disappears on a record that has reached a terminal state — there
    # is nothing ahead to walk to, so every intermediate step would rest on
    # Version history alone, and that is absent whenever the DocType does not
    # track changes. The whole transition list is used rather than `live`: the
    # record demonstrably arrived here, so some inbound route exists and must
    # be drawn even if its condition no longer holds.
    relevant |= _reachable(transitions, current_state, reverse=True)

    kept_states = [s for s in states if s["name"] in relevant]
    kept_names = {s["name"] for s in kept_states}

    # Re-index so step numbers stay contiguous after states are removed. The
    # relative order is preserved, which is what the client's layering uses.
    for idx, state in enumerate(kept_states):
        state["order"] = idx

    kept_transitions = [
        t for t in live if t["from_state"] in kept_names and t["to_state"] in kept_names
    ]

    return kept_states, kept_transitions


def _condition_satisfied(transition, doc):
    """Whether a transition's condition currently holds.

    A transition with no condition is always satisfied. Conditions are
    evaluated through Frappe's own sandbox, never a bare eval().
    """
    if not transition.condition:
        return True
    if doc is None:
        # Without a document there is nothing to evaluate against; treat the
        # edge as possible so the full graph still renders on a new form.
        return True
    try:
        return bool(is_transition_condition_satisfied(transition, doc))
    except Exception:
        # A broken condition should not blank out the whole progress bar.
        frappe.log_error(
            title="Workflow progress: condition evaluation failed",
            message=frappe.get_traceback(),
        )
        return False


def _comment_history(doctype, docname, transitions, first_state):
    """Reconstruct who entered each state by replaying the comment trail.

    ``apply_workflow`` records a Comment of type "Workflow" for every action
    taken, carrying the acting user and the time. The comment text is the
    *translated* action name, so it cannot be matched against the transition
    table on a multilingual site; instead the trail is replayed in order,
    advancing one transition per comment.

    The replay stops at the first fork it cannot resolve rather than guessing
    which branch was taken — a wrong name against a step is worse than none.
    """
    if not first_state:
        return {}

    try:
        rows = frappe.get_all(
            "Comment",
            filters={
                "reference_doctype": doctype,
                "reference_name": docname,
                "comment_type": "Workflow",
            },
            fields=["owner", "creation", "content"],
            order_by="creation asc",
        )
    except Exception:
        return {}

    outgoing = {}
    for transition in transitions:
        outgoing.setdefault(transition["from_state"], []).append(transition)

    entered = {}
    position = first_state

    for row in rows:
        options = outgoing.get(position) or []
        target = None

        if len(options) == 1:
            # Only one way out — the comment can only mean this step.
            target = options[0]["to_state"]
        else:
            # A fork: fall back to the action name, which may be translated.
            content = (row.content or "").strip()
            matches = [
                o for o in options if (o.get("action") or "").strip() == content
            ]
            if len(matches) == 1:
                target = matches[0]["to_state"]

        if not target:
            break

        entered[target] = {"user": row.owner, "on": str(row.creation)}
        position = target

    return entered


def _workflow_action_history(doctype, docname):
    """Who completed the action raised at each state.

    Frappe raises a Workflow Action whenever a document enters a state that has
    outgoing transitions, and stamps `completed_by` when somebody acts on it.
    These rows exist regardless of whether the DocType tracks changes, so they
    fill in the steps that Version history cannot account for.

    Returns ``state -> {user, on}``. Several rows can exist for one state (one
    per permitted user); ordering by `modified` means the row that actually
    completed the step wins.
    """
    try:
        rows = frappe.get_all(
            "Workflow Action",
            filters={
                "reference_doctype": doctype,
                "reference_name": docname,
                "status": "Completed",
            },
            fields=["workflow_state", "completed_by", "modified"],
            order_by="modified asc",
        )
    except Exception:
        # Never let an unexpected schema take down the whole progress bar.
        return {}

    handled = {}
    for row in rows:
        if row.workflow_state and row.completed_by:
            handled[row.workflow_state] = {
                "user": row.completed_by,
                "on": str(row.modified),
            }
    return handled


def _state_history(
    doctype, docname, state_field, states, current_state=None, transitions=None
):
    """Who moved the document into each state, and when.

    Reads the Version rows Frappe writes on every field change. Returns a map
    of ``state -> {user, on, seq}``. Permission on the parent document has
    already been checked by the caller.
    """
    if not docname:
        return {}

    history = {}

    stamps = frappe.db.get_value(
        doctype,
        docname,
        ["owner", "creation", "modified_by", "modified"],
        as_dict=True,
    )

    # The opening state is not a transition — it is the document's creation.
    if stamps and states:
        history[states[0]["name"]] = {
            "user": stamps.owner,
            "on": str(stamps.creation),
            "seq": 0,
        }

    rows = frappe.get_all(
        "Version",
        filters={"ref_doctype": doctype, "docname": docname},
        fields=["owner", "creation", "data"],
        order_by="creation asc",
    )

    for row in rows:
        try:
            data = json.loads(row.data or "{}")
        except (ValueError, TypeError):
            continue
        for change in data.get("changed") or []:
            # change is [fieldname, old_value, new_value]
            if len(change) >= 3 and change[0] == state_field and change[2]:
                history[change[2]] = {
                    "user": row.owner,
                    "on": str(row.creation),
                    "seq": len(history),
                }

    # Replaying the comment trail attributes the state each action *entered*,
    # matching what Version records, so it is preferred over Workflow Action.
    if states:
        for state, entered in _comment_history(
            doctype, docname, transitions or [], states[0]["name"]
        ).items():
            if state not in history:
                history[state] = {
                    "user": entered["user"],
                    "on": entered["on"],
                    "seq": len(history),
                }

    # Version rows only exist when the DocType tracks changes. Workflow Actions
    # are written either way, so they fill in every step still missing. Note
    # these attribute the state acted *from*, not the one entered.
    for state, handled in _workflow_action_history(doctype, docname).items():
        if state not in history:
            history[state] = {
                "user": handled["user"],
                "on": handled["on"],
                "seq": len(history),
            }

    # The document sits on `current_state` now, so that step should always be
    # attributable. Nothing records the move while the action there is still
    # open, so fall back to whoever last touched the document.
    if current_state and current_state not in history and stamps:
        history[current_state] = {
            "user": stamps.modified_by,
            "on": str(stamps.modified),
            "seq": len(history),
        }

    return history


# ---------------------------------------------------------------------------
# Deprecated — kept so existing client scripts keep working
# ---------------------------------------------------------------------------


def normalize_state(state):
    """Normalize state for case-insensitive comparison"""
    return state.lower().strip() if state else ""


def find_matching_state(existing_states, target_state):
    """Find a state in existing_states that matches target_state case-insensitively"""
    target_normalized = normalize_state(target_state)
    for state in existing_states:
        if normalize_state(state) == target_normalized:
            return state
    return None


def replace_state(result, old_state, new_state):
    """Replace old_state with new_state in workflow transitions (case-insensitive)"""
    updated_result = []
    old_normalized = normalize_state(old_state)

    for state, next_states in result:
        current_state = new_state if normalize_state(state) == old_normalized else state

        updated_next = []
        for next_state in next_states:
            if normalize_state(next_state) == old_normalized:
                updated_next.append(new_state)
            else:
                updated_next.append(next_state)

        updated_result.append((current_state, tuple(updated_next)))

    seen_normalized = set()
    final_result = []
    for state, next_states in updated_result:
        state_normalized = normalize_state(state)
        if state_normalized not in seen_normalized:
            seen_normalized.add(state_normalized)
            final_result.append((state, next_states))

    return final_result


def get_complete_workflow_paths(ordered_transitions):
    """Generate all complete paths from start states to end states."""
    transitions_dict = {}
    all_states = set()

    for from_state, to_state in ordered_transitions:
        transitions_dict.setdefault(from_state, []).append(to_state)
        all_states.add(from_state)
        all_states.add(to_state)

    to_states = {to for _, to in ordered_transitions}
    start_states = all_states - to_states

    from_states = {from_state for from_state, _ in ordered_transitions}
    end_states = all_states - from_states

    def find_paths(current_state, path):
        if current_state in end_states:
            return [path + [current_state]]
        if current_state not in transitions_dict:
            return [path + [current_state]]

        paths = []
        for next_state in transitions_dict[current_state]:
            if next_state not in path:  # Avoid cycles
                paths.extend(find_paths(next_state, path + [current_state]))
        return paths

    all_paths = []
    for start in start_states:
        all_paths.extend(find_paths(start, []))

    return all_paths


@frappe.whitelist()
def get_workflow_states(workflow_name, docname=None):
    """DEPRECATED — use :func:`get_workflow_graph` instead.

    Collapses the workflow into a single linear chain and hides rejection
    states unless the document currently sits on one, so branches are lost.
    Retained only so existing client scripts keep working.
    """
    workflow = frappe.get_doc("Workflow", workflow_name)

    doc = None
    workflow_state = None
    doctype = workflow.document_type
    if doctype and docname:
        doc = frappe.get_doc(doctype, docname)
        doc.check_permission("read")
        workflow_state = doc.get(workflow.workflow_state_field or "workflow_state")

    ordered_transitions = [
        (tran.state, tran.next_state)
        for tran in workflow.transitions
        if tran.state == "Draft" or _condition_satisfied(tran, doc)
    ]

    flows = get_complete_workflow_paths(ordered_transitions)

    transitions = {}
    for flow in flows:
        for i in range(len(flow) - 1):
            transitions.setdefault(flow[i], set()).add(flow[i + 1])

    all_states = set()
    for flow in flows:
        all_states.update(flow)

    state_order = {state.state: idx for idx, state in enumerate(workflow.states)}

    rejection_pattern = re.compile(r"reject", re.IGNORECASE)

    def is_rejection_state(state):
        return bool(rejection_pattern.search(state))

    filtered_states = set()
    for state in all_states:
        if is_rejection_state(state):
            if workflow_state and normalize_state(state) == normalize_state(
                workflow_state
            ):
                filtered_states.add(state)
        else:
            filtered_states.add(state)

    result = []
    for state in sorted(filtered_states, key=lambda x: state_order.get(x, 999)):
        if state in transitions:
            filtered_next_states = set()
            for next_state in transitions[state]:
                if is_rejection_state(next_state):
                    if workflow_state and normalize_state(
                        next_state
                    ) == normalize_state(workflow_state):
                        filtered_next_states.add(next_state)
                else:
                    filtered_next_states.add(next_state)

            sorted_next_states = sorted(
                filtered_next_states, key=lambda x: state_order.get(x, 999)
            )
            result.append((state, tuple(sorted_next_states)))
        else:
            result.append((state, ()))

    rejection_states = [state for state, _ in result if is_rejection_state(state)]
    if rejection_states:
        rejection_state = rejection_states[0]

        approve_pattern = rejection_pattern.sub("Approved", rejection_state, count=1)
        approve_state = find_matching_state(all_states, approve_pattern)

        if not approve_state:
            for pattern in [
                rejection_state.replace("Rejected", "Approved"),
                rejection_state.replace("rejected", "approved"),
                rejection_state.replace("REJECTED", "APPROVED"),
                "Approved",
            ]:
                approve_state = find_matching_state(all_states, pattern)
                if approve_state:
                    break

        if approve_state:
            return replace_state(result, approve_state, rejection_state)

    return result




@frappe.whitelist()
def get_reserved_slots(start_date=None, end_date=None):
    """
    Whitelisted API to fetch car wash reservations.
    Runs with ignore_permissions to show all bookings regardless of user role.
    ⚠️ Use cautiously - ensure this endpoint is not exposed publicly.
    """
    if not start_date or not end_date:
        return []

    
    slots = frappe.get_all(
        'Request Car Wash',
        fields=['name', 'request_date', 'employee_name', 'status'],  # Add fields you need
        filters=[
            ['request_date', '>=', f'{start_date} 00:00:00'],
            ['request_date', '<=', f'{end_date} 23:59:59']
        ],
        order_by='request_date asc',
        limit=500,
        ignore_permissions=True  # 👈 This bypasses permission checks
    )
    slots = [slot['request_date'].strftime('%Y-%m-%d %H:%M:%S') for slot in slots ]
    return slots

import io
import frappe
from frappe.utils.pdf import get_pdf
from pypdf import PdfReader, PdfWriter

@frappe.whitelist()
def apply_dynamic_stamp(doc_name, stamp_text):
    """
    Apply a stamp to a Printing Permit Request document.
    Expects doc_name and stamp_text as arguments
    """
    
    # Validate required arguments
    if not doc_name:
        return {"status": "error", "message": "doc_name is required"}
    if not stamp_text:
        return {"status": "error", "message": "stamp_text is required"}
    
    try:
        # Get the document
        doc = frappe.get_doc("Printing Permit Request", doc_name)
        
        # Validate that PDF exists
        if not doc.get("attached_pdf"):
            return {"status": "error", "message": "خطأ: يرجى إرفاق ملف PDF الأصلي قبل الاعتماد."}
        
        # Get the original file path
        original_file = frappe.get_doc("File", {"file_url": doc.get("attached_pdf")})
        original_file_path = original_file.get_full_path()
        
        # Get field values
        approval_date = doc.get("approval_date") or frappe.utils.today()
        name = doc.get("name")
        book_title = doc.get("book_title") or ""
        author = doc.get("author") or ""
        
        # Design stamp HTML
        stamp_html = f"""
        <html>
        <head>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: Arial, sans-serif;
                }}
                .stamp-box {{
                    position: absolute;
                    top: 450px;
                    left: 150px;
                    border: 2px solid #c9302c;
                    color: #c9302c;
                    padding: 15px;
                    width: 320px;
                    direction: rtl;
                    background-color: rgba(255, 255, 255, 0.85);
                    transform: rotate(-2deg);
                }}
                .stamp-header {{
                    text-align: center;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 10px;
                    line-height: 1.4;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    font-size: 13px;
                    color: #c9302c;
                }}
                td {{
                    padding: 3px 0;
                    vertical-align: top;
                }}
                .handwritten {{
                    color: #2c3e50;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="stamp-box">
                <div class="stamp-header">
                    الجمهورية العربية السورية<br>
                    وزارة الإعلام<br>
                    إدارةالشؤون الصحفية والتراخيص<br>
                    دائرة المطبوعات
                </div>
                <table>
                    <tr>
                        <td style="width: 80px;">التاريخ:</td>
                        <td class="handwritten">{approval_date}</td>
                    </tr>
                    <tr>
                        <td>رقم:</td>
                        <td class="handwritten">{name}</td>
                    </tr>
                    <tr>
                        <td>اسم الكتاب:</td>
                        <td class="handwritten">{book_title}</td>
                    </tr>
                    <tr>
                        <td>المؤلف:</td>
                        <td class="handwritten">{author}</td>
                    </tr>
                    <tr>
                        <td>التأشيرة:</td>
                        <td class="handwritten">{stamp_text}</td>
                    </tr>
                    <tr>
                        <td>الاسم والتوقيع:</td>
                        <td class="handwritten">.........................</td>
                    </tr>
                </table>
            </div>
        </body>
        </html>
        """
        
        # Convert HTML to PDF
        pdf_options = {
            "page-size": "A4",
            "margin-top": "0mm",
            "margin-bottom": "0mm",
            "margin-left": "0mm",
            "margin-right": "0mm",
            "encoding": "UTF-8"
        }
        stamp_pdf_bytes = get_pdf(stamp_html, options=pdf_options)
        
        # Merge stamp with original PDF
        original_pdf_reader = PdfReader(original_file_path)
        stamp_pdf_reader = PdfReader(io.BytesIO(stamp_pdf_bytes))
        pdf_writer = PdfWriter()
        
        # Merge first page only
        first_page = original_pdf_reader.pages[0]
        stamp_page = stamp_pdf_reader.pages[0]
        first_page.merge_page(stamp_page)
        pdf_writer.add_page(first_page)
        
        # Add remaining pages
        for page_num in range(1, len(original_pdf_reader.pages)):
            pdf_writer.add_page(original_pdf_reader.pages[page_num])
        
        output_buffer = io.BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        # Save the new stamped file
        new_file_name = f"Stamped_{doc.get('name')}.pdf"
        stamped_file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": new_file_name,
            "attached_to_doctype": "Printing Permit Request",
            "attached_to_name": doc.get("name"),
            "attached_to_field": "stamped_pdf",
            "content": output_buffer.getvalue(),
            "is_private": original_file.is_private
        })
        stamped_file_doc.insert(ignore_permissions=True)
        
        # Update the document with the stamped file URL
        frappe.db.set_value("Printing Permit Request", doc_name, "stamped_pdf", stamped_file_doc.file_url)
        frappe.db.commit()
        
        return {
            "status": "success",
            "message": f"تم إرفاق الختم بنجاح بحالة: {stamp_text}",
            "stamped_pdf": stamped_file_doc.file_url
        }
        
    except Exception as e:
        frappe.log_error(f"Error applying stamp: {str(e)}", "Printing Stamp Error")
        return {
            "status": "error",
            "message": f"حدث خطأ أثناء تطبيق الختم: {str(e)}"
        }

import frappe
import json


@frappe.whitelist()
def create_doc_in_state(doctype, doc, target_workflow_state=None):
    """Create a doc and place it directly into a target workflow state.

    Frappe blocks:
      - inserting with a workflow_state != initial state, and
      - saving a transition that isn't defined (e.g. "Not Saved" -> "Pending Review").

    So we insert WITHOUT workflow_state, then set it via a direct DB update,
    which does NOT run validate / workflow checks.
    """
    if isinstance(doc, str):
        doc = json.loads(doc)

    # Never send workflow_state on insert -> avoids "Not Saved" transition error
    doc.pop("workflow_state", None)
    doc["doctype"] = doctype

    d = frappe.get_doc(doc)
    d.insert(ignore_permissions=True)

    if target_workflow_state:
        # Direct DB UPDATE -> bypasses workflow transition validation
        frappe.db.set_value(
            doctype,
            d.name,
            "workflow_state",
            target_workflow_state,
            update_modified=False,
        )

    return d.name