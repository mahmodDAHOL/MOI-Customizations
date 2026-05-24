import pyqrcode
import io
import frappe
import base64
import re
import os
from frappe.utils.file_manager import save_file
from urllib.parse import urlparse

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

async def _html_to_pdf_bytes(html_content: str) -> bytes:
    """Convert HTML string to PDF bytes using Playwright (Chromium)."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()

        # Set viewport to match A4 size (optional but recommended)
        await page.set_viewport_size({"width": 794, "height": 1123})

        # Set content
        await page.set_content(html_content)
        # await page.screenshot(path="mahmod.png")
        # Generate PDF with high-fidelity settings
        pdf_bytes = await page.pdf(
            scale=1.0,
            print_background=True,
            width="210mm",
            height="297mm",
            margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
            display_header_footer=True,
            prefer_css_page_size=True
        )

        await browser.close()
        return pdf_bytes

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
        if row['item_type']!='أسلحة و معدات حماية' and desc:
            for td in soup.find_all('td'):
                if td.get_text(strip=True) == 'الشركة المصنعة':
                    # Get the previous sibling td (the one before this td)
                    prev_td = td.find_previous_sibling('td')
                    if prev_td:
                        manufacturer = prev_td.get_text(strip=True)
                        row['manufacturer'] = manufacturer
                        row['item_name_with_manufacturer'] = f"{row['item_name']} \n {manufacturer}" if manufacturer else row['item_name']
        else:
            row['item_name_with_manufacturer'] = row['item_name']

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
    Returns: {'user_id': 'user@domain.com'} or {'error': 'message'}
    """
    if not employee:
        return {"error": _("No employee specified")}
    
    # Validate employee exists
    if not frappe.db.exists("Employee", employee):
        return {"error": _("Employee {0} not found").format(employee)}
    
    current_emp = employee
    max_depth = 10  # Prevent infinite loops in circular reporting structures
    visited = set()  # Detect circular references
    
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
                        return {"user_id": manager_user, "level": depth + 1, "verified": True}
                
                # Fallback: Return found user even if not department_head field (role-based match)
                return {"user_id": manager_user, "level": depth + 1, "verified": False}
        except Exception as e:
            frappe.log_error(
                f"Error checking roles for {manager_user}: {str(e)}",
                "get_department_head_approver"
            )
        
        # Move up the chain
        current_emp = manager_emp
    
    # Final fallback: Try direct department head lookup
    applicant_dept = frappe.db.get_value("Employee", employee, "department")
    if applicant_dept:
        dept_head_user = frappe.db.get_value("Department", applicant_dept, "department_head")
        if dept_head_user and frappe.db.exists("User", dept_head_user):
            return {
                "user_id": dept_head_user, 
                "level": "direct", 
                "verified": True,
                "source": "department_head_field"
            }
    
    return {
        "error": "No approver with 'Head of Department' role found in reporting chain (max depth: {0})".format(max_depth),
        "chain_depth": depth + 1
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


import re

def normalize_state(state):
    """Normalize state for case-insensitive comparison"""
    return state.lower().strip() if state else ''

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
        # Replace in current state
        current_state = new_state if normalize_state(state) == old_normalized else state
        
        # Replace in next states
        updated_next = []
        for next_state in next_states:
            if normalize_state(next_state) == old_normalized:
                updated_next.append(new_state)
            else:
                updated_next.append(next_state)
        
        updated_result.append((current_state, tuple(updated_next)))
    
    # Remove duplicates if any (case-insensitive)
    seen_normalized = set()
    final_result = []
    for state, next_states in updated_result:
        state_normalized = normalize_state(state)
        if state_normalized not in seen_normalized:
            seen_normalized.add(state_normalized)
            final_result.append((state, next_states))
    
    return final_result


@frappe.whitelist()
def get_workflow_states(workflow_name, docname=None):
    """
    Get workflow states with filtering for rejection states (case-insensitive).
    """
    
    workflow = frappe.get_doc('Workflow', workflow_name)
    
    # Get current workflow_state
    workflow_state = None
    doctype = workflow.document_type
    if doctype and docname:
        doc = frappe.get_doc(doctype, docname)
        workflow_state = frappe.db.get_value(doctype, docname, 'workflow_state')

    ordered_transitions = [(tran.state, tran.next_state) for tran in workflow.transitions 
                            if tran.state == "Draft" or
                                evaluate_condition(tran.condition, doc)]

    flows = get_complete_workflow_paths(ordered_transitions)
    # Remove duplicates from flows
    unique_flows = []
    for flow in flows:
        if flow not in unique_flows:
            unique_flows.append(flow)

    transitions = {}
    for flow in flows:
        for i in range(len(flow) - 1):
            current = flow[i]
            next_state = flow[i + 1]
            
            if current not in transitions:
                transitions[current] = set()
            transitions[current].add(next_state)
    # Get all states
    all_states = set()
    for flow in flows:
        all_states.update(flow)

    # Get state order from workflow.states
    state_order = {}
    for idx, state in enumerate(workflow.states):
        state_order[state.state] = idx
    
    # Define rejection keywords (lowercase for case-insensitive matching)
    rejection_pattern = re.compile(r'reject', re.IGNORECASE)
    
    def is_rejection_state(state):
        """Check if a state is a rejection state (case-insensitive)"""
        return bool(rejection_pattern.search(state))
    
    # Filter states based on rejection rules
    filtered_states = set()
    for state in all_states:
        if is_rejection_state(state):
            # Only include rejection state if it matches current workflow_state (case-insensitive)
            if workflow_state and normalize_state(state) == normalize_state(workflow_state):
                filtered_states.add(state)
        else:
            # Always include non-rejection states
            filtered_states.add(state)
    
    # Build result
    result = []
    for state in sorted(filtered_states, key=lambda x: state_order.get(x, 999)):
        if state in transitions:
            filtered_next_states = set()
            for next_state in transitions[state]:
                if is_rejection_state(next_state):
                    if workflow_state and normalize_state(next_state) == normalize_state(workflow_state):
                        filtered_next_states.add(next_state)
                else:
                    filtered_next_states.add(next_state)
            
            sorted_next_states = sorted(filtered_next_states, key=lambda x: state_order.get(x, 999))
            result.append((state, tuple(sorted_next_states)))
        else:
            result.append((state, tuple()))

    # Handle rejection states replacement
    rejection_states = [state for state, _ in result if is_rejection_state(state)]
    if rejection_states:
        rejection_state = rejection_states[0]
        
        # Find matching approve state (case-insensitive)
        approve_state = None
        approve_pattern = rejection_pattern.sub('Approved', rejection_state, count=1)
        
        # Try to find matching approve state in all_states
        approve_state = find_matching_state(all_states, approve_pattern)
        
        if not approve_state:
            # Try alternative patterns
            for pattern in [rejection_state.replace('Rejected', 'Approved'),
                           rejection_state.replace('rejected', 'approved'),
                           rejection_state.replace('REJECTED', 'APPROVED'),
                           'Approved']:
                approve_state = find_matching_state(all_states, pattern)
                if approve_state:
                    break
        
        if approve_state:
            new_result = replace_state(result, approve_state, rejection_state)
            return new_result
    return result


def evaluate_condition(condition, doc):
    """
    Evaluate condition - session.user comparisons always True
    Handles AND/OR by splitting the condition
    """
    
    # Helper to evaluate a single condition part
    def eval_part(part):
        part = part.strip()
        if 'frappe.session.user' in part or 'frappe.user.session' in part:
            # Session user comparison always returns True for ==
            if '==' in part and '!=' not in part:
                return True
            elif '!=' in part:
                return False
            return True
        # Evaluate non-session conditions
        return eval(part, {'doc': doc, 'frappe': frappe})
    
    # Split by AND
    if ' and ' in condition.lower():
        parts = re.split(r'\s+and\s+', condition, flags=re.IGNORECASE)
        return all(eval_part(part) for part in parts)
    
    # Split by OR
    elif ' or ' in condition.lower():
        parts = re.split(r'\s+or\s+', condition, flags=re.IGNORECASE)
        return any(eval_part(part) for part in parts)
    
    # Single condition
    else:
        return eval_part(condition)


def get_complete_workflow_paths(ordered_transitions):
    
    """
    Generate all complete workflow paths from start states to end states
    
    Args:
        ordered_transitions: List of tuples [(from_state, to_state), ...]
    
    Returns:
        List of complete paths from start to end
    """
    # Build adjacency list
    transitions_dict = {}
    all_states = set()
    
    for from_state, to_state in ordered_transitions:
        if from_state not in transitions_dict:
            transitions_dict[from_state] = []
        transitions_dict[from_state].append(to_state)
        all_states.add(from_state)
        all_states.add(to_state)
    
    # Find start states (states that never appear as 'to' except as 'from')
    to_states = {to for _, to in ordered_transitions}
    start_states = all_states - to_states
    
    # Find end states (states that never appear as 'from')
    from_states = {from_state for from_state, _ in ordered_transitions}
    end_states = all_states - from_states
    
    # Generate all paths from start to end
    def find_paths(current_state, path):
        """Recursively find all paths from current_state to end states"""
        paths = []
        
        if current_state in end_states:
            return [path + [current_state]]
        
        if current_state not in transitions_dict:
            return [path + [current_state]]
        
        for next_state in transitions_dict[current_state]:
            if next_state not in path:  # Avoid cycles
                extended_paths = find_paths(next_state, path + [current_state])
                paths.extend(extended_paths)
        
        return paths
    
    # Get all paths from all start states
    all_paths = []
    for start in start_states:
        paths = find_paths(start, [])
        all_paths.extend(paths)
    
    return all_paths

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