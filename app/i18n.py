"""
ThaiBill - i18n (TH ↔ EN)
ใช้ภาษาไทยเป็น key ถ้าไม่เจอ translation จะ fallback เป็น key เดิม
"""
from flask import request

# ทุก string ที่ขึ้นจอที่ต้องแปล
EN = {
    # === Nav / sidebar ===
    'แดชบอร์ด': 'Dashboard',
    'เอกสารขาย': 'Sales Documents',
    'ใบเสนอราคา': 'Quotation',
    'ใบแจ้งหนี้': 'Invoice',
    'ใบส่งของ': 'Delivery Order',
    'ใบกำกับภาษี': 'Tax Invoice',
    'ใบเสร็จรับเงิน': 'Receipt',
    'ฐานข้อมูล': 'Database',
    'ลูกค้า': 'Customers',
    'สินค้า / บริการ': 'Products / Services',
    'สินค้า/บริการ': 'Products/Services',
    'ตั้งค่า': 'Settings',
    'ข้อมูลกิจการ': 'Company Info',
    'หน้าแรก': 'Home',
    'สร้างเอกสาร': 'New Document',

    # === Generic actions ===
    'บันทึก': 'Save',
    'ยกเลิก': 'Cancel',
    'แก้ไข': 'Edit',
    'ลบ': 'Delete',
    'เพิ่ม': 'Add',
    'ค้นหา': 'Search',
    'ดู': 'View',
    'พิมพ์': 'Print',
    'ดาวน์โหลด': 'Download',
    'อัปโหลด': 'Upload',
    'ย้อนกลับ': 'Back',
    'ถัดไป': 'Next',
    'ตกลง': 'OK',
    'เรียบร้อย': 'Done',
    'เพิ่มรายการ': 'Add Item',
    'ทำสำเนา': 'Duplicate',
    'แปลงเป็น': 'Convert to',
    'ล่าสุด': 'Latest',
    'ทั้งหมด': 'Total',
    'รายการ': 'items',
    'ราย': 'records',
    'เข้าสู่ระบบ': 'Sign In',
    'ออกจากระบบ': 'Sign Out',
    'จดจำการเข้าระบบ': 'Remember me',
    'ชื่อผู้ใช้': 'Username',
    'รหัสผ่าน': 'Password',
    'เข้าใช้เป็น': 'Logged in as',

    # === Document fields ===
    'เลขที่': 'Number',
    'วันที่': 'Date',
    'วันที่ออก': 'Issue Date',
    'ยืนราคาถึง': 'Valid Until',
    'ครบกำหนดชำระ': 'Due Date',
    'วันที่ส่งของ': 'Delivery Date',
    'วันที่ออกใบกำกับภาษี': 'Tax Invoice Date',
    'วันที่ออกใบกำกับ': 'Tax Invoice Date',
    'วันที่รับชำระ': 'Payment Date',
    'เลขอ้างอิง': 'Reference No.',
    'อ้างอิง': 'Reference',
    'ชื่อโครงการ / เรื่อง': 'Project / Subject',
    'โครงการ': 'Project',
    'หมายเหตุ': 'Note',
    'เงื่อนไข': 'Terms',
    'รายละเอียด': 'Description',
    'รายละเอียดเพิ่มเติม': 'Additional details',
    'ที่อยู่จัดส่ง': 'Delivery Address',
    'ที่อยู่จัดส่ง (ถ้าต่างจากที่อยู่ลูกค้า)': 'Delivery Address (if different)',
    'ชื่อผู้รับสินค้า': 'Receiver Name',
    'ผู้รับสินค้า': 'Receiver',
    'วิธีการชำระเงิน': 'Payment Method',
    'วิธีชำระ': 'Method',
    'เงินสด': 'Cash',
    'โอนเงิน': 'Bank Transfer',
    'เช็ค': 'Cheque',
    'บัตรเครดิต': 'Credit Card',
    'อื่นๆ': 'Other',
    'เลขที่เช็ค / อ้างอิงการโอน': 'Cheque No. / Reference',
    'จำนวนเงินที่รับ': 'Amount Received',
    'การจัดส่ง': 'Shipping',
    'การรับชำระเงิน': 'Payment Details',
    'การชำระเงิน': 'Payment',

    # === Items / totals ===
    'จำนวน': 'Qty',
    'หน่วย': 'Unit',
    'ราคา/หน่วย': 'Unit Price',
    'ราคา': 'Price',
    'ราคาขาย': 'Sale Price',
    'ต้นทุน': 'Cost',
    'ลด %': 'Discount %',
    'รวม': 'Total',
    'มูลค่ารวม': 'Subtotal',
    'ส่วนลดท้ายบิล': 'Discount',
    'หลังหักส่วนลด': 'After Discount',
    'ภาษีมูลค่าเพิ่ม': 'VAT',
    'ยอดสุทธิ': 'Grand Total',
    'ยอด': 'Amount',
    'สรุปยอด': 'Summary',
    'ราคารวม VAT แล้ว': 'Prices include VAT',
    'VAT เริ่มต้น (%)': 'Default VAT (%)',

    # === Customer ===
    'ลูกค้า ': 'Customer ',  # with space to avoid collision
    'ชื่อลูกค้า': 'Customer Name',
    'ชื่อลูกค้า / กิจการ': 'Customer / Company Name',
    'ชื่อกิจการ': 'Company Name',
    'รหัสลูกค้า': 'Customer Code',
    'รหัส': 'Code',
    'เลขประจำตัวผู้เสียภาษี': 'Tax ID',
    'เลขผู้เสียภาษี': 'Tax ID',
    'สาขา': 'Branch',
    'สำนักงานใหญ่': 'Head Office',
    'ผู้ติดต่อ': 'Contact Person',
    'ติดต่อ': 'Contact',
    'โทรศัพท์': 'Phone',
    'อีเมล': 'Email',
    'เว็บไซต์': 'Website',
    'ที่อยู่': 'Address',
    'ประเภท': 'Type',
    'นิติบุคคล': 'Company',
    'บุคคลธรรมดา': 'Individual',
    'เครดิต (วัน)': 'Credit (days)',
    'สินค้า': 'Goods',
    'บริการ': 'Service',
    'ชื่อ': 'Name',

    # === Status labels ===
    'สถานะ': 'Status',
    'ทุกสถานะ': 'All statuses',
    'ร่าง': 'Draft',
    'ส่งให้ลูกค้า': 'Sent',
    'ลูกค้าตอบรับ': 'Accepted',
    'ลูกค้าปฏิเสธ': 'Rejected',
    'หมดอายุ': 'Expired',
    'ออกเอกสารแล้ว': 'Converted',
    'ชำระแล้ว': 'Paid',
    'ชำระบางส่วน': 'Partially Paid',
    'เกินกำหนด': 'Overdue',
    'ส่งสินค้าแล้ว': 'Shipped',
    'ส่งถึงปลายทาง': 'Delivered',
    'ออกแล้ว': 'Issued',

    # === Dashboard ===
    'ใบเสนอราคา (เดือนนี้)': 'Quotations (this month)',
    'ยอดค้างชำระ': 'Outstanding',
    'รับชำระเดือนนี้': 'Received (this month)',
    'ใบเสนอราคารอติดตาม': 'Pending Quotations',
    'ดูทั้งหมด': 'View all',
    'ดูใบแจ้งหนี้': 'View invoices',
    'ดูใบเสร็จ': 'View receipts',
    'รายละเอียด': 'Details',
    'ใบแจ้งหนี้ 14 วันล่าสุด': 'Invoices - last 14 days',
    'เอกสารล่าสุด': 'Recent Documents',
    'สรุปจำนวนเอกสาร': 'Document Counts',
    'ลิงก์ลัด': 'Quick Links',
    'สร้างใบเสนอราคา': 'New Quotation',
    'สร้างใบแจ้งหนี้': 'New Invoice',
    'เพิ่มลูกค้า': 'Add Customer',
    'เพิ่มสินค้า / บริการ': 'Add Product/Service',
    'เพิ่มลูกค้าใหม่': 'Add New Customer',
    'เพิ่มสินค้า/บริการ': 'Add Product/Service',
    'สร้างใบเสนอราคาใบแรก': 'Create first quotation',
    'เพิ่มลูกค้ารายแรก': 'Add first customer',
    'เพิ่มรายการแรก': 'Add first item',

    # === Documents view ===
    'เปลี่ยนสถานะ': 'Change Status',
    'เอกสารที่แปลงไป': 'Converted Documents',
    'ข้อมูลเอกสาร': 'Document Info',
    'สร้างเมื่อ': 'Created',
    'แก้ไขล่าสุด': 'Last Updated',
    'เอกสารนี้ออกจาก': 'This document was created from',
    'ทำสำเนาเอกสาร': 'Duplicate document',
    'ลบเอกสาร': 'Delete document',
    'ยืนยันการลบเอกสาร': 'Confirm delete document',

    # === Document list ===
    'ยอดสุทธิ': 'Total',
    'ยังไม่มี': 'No',
    'ยังไม่มีเอกสาร': 'No documents yet',
    'ยังไม่มีลูกค้า': 'No customers yet',
    'ยังไม่มีสินค้า/บริการ': 'No products/services yet',

    # === Document form ===
    'สร้าง': 'Create',
    'ใหม่': 'new',
    'เลขที่จะถูกสร้างอัตโนมัติเมื่อบันทึก': 'Number will be generated when saved',

    # === Settings ===
    'ตั้งค่าข้อมูลกิจการ': 'Company Settings',
    'ข้อมูลธนาคาร (สำหรับใบแจ้งหนี้)': 'Bank Info (for invoices)',
    'เงื่อนไขเริ่มต้น': 'Default Terms',
    'บันทึกการตั้งค่า': 'Save Settings',
    'เกี่ยวกับ': 'About',
    'ระบบเอกสารขายภาษาไทย รองรับ': 'Online accounting software supporting:',
    'โลโก้บริษัท': 'Company Logo',
    'อัปโหลดโลโก้': 'Upload Logo',
    'เปลี่ยนโลโก้': 'Change Logo',
    'ลบโลโก้': 'Remove Logo',
    'ยังไม่มีโลโก้': 'No logo yet',
    'โลโก้จะแสดงในหัวเอกสาร PDF ทุกประเภท': 'Logo will appear in PDF header of all documents',
    'ลายเซ็น (ผู้มีอำนาจ)': 'Signature (Authorized)',
    'ลายเซ็น': 'Signature',
    'อัปโหลดลายเซ็น': 'Upload Signature',
    'เปลี่ยนลายเซ็น': 'Change Signature',
    'ลบลายเซ็น': 'Remove Signature',
    'ยังไม่มีลายเซ็น': 'No signature yet',

    # === Preferences (new) ===
    'ภาษาและธีม': 'Language & Theme',
    'ภาษา': 'Language',
    'ธีมสี': 'Color Theme',
    'ภาษาไทย': 'Thai',
    'English': 'English',

    # === Backup/Restore (new) ===
    'สำรองและกู้คืน': 'Backup & Restore',
    'สำรองข้อมูล': 'Backup',
    'ดาวน์โหลดสำรอง': 'Download Backup',
    'ดาวน์โหลดไฟล์ .zip ที่มีข้อมูลทั้งหมด (database + รูปอัปโหลด)':
        'Download a .zip file with all data (database + uploaded files)',
    'กู้คืนข้อมูล': 'Restore Data',
    'อัปโหลดไฟล์ .zip ที่เคยสำรองไว้': 'Upload a previously created backup .zip',
    'เลือกไฟล์ .zip': 'Choose .zip file',
    'กู้คืน': 'Restore',
    'คำเตือน': 'Warning',
    'การกู้คืนจะเขียนทับข้อมูลปัจจุบันทั้งหมด': 'Restoring will overwrite all current data',
    'แนะนำให้สำรองข้อมูลปัจจุบันก่อน': 'Recommended to backup current data first',

    # === Google Drive (new) ===
    'เชื่อมต่อ Google Drive': 'Google Drive Integration',
    'อัปโหลดสำรองไปยัง Google Drive': 'Upload backup to Google Drive',
    'อัปโหลดไปยัง Google Drive': 'Upload to Google Drive',
    'รหัสโฟลเดอร์ Google Drive': 'Google Drive Folder ID',
    'อีเมล Service Account': 'Service Account Email',
    'ทดสอบการเชื่อมต่อ': 'Test Connection',
    'เชื่อมต่อสำเร็จ': 'Connection successful',
    'ยังไม่ได้ตั้งค่า': 'Not configured',
    'อัปโหลดไฟล์ Service Account JSON': 'Upload Service Account JSON',

    # === Misc ===
    'พิมพ์เพื่อค้นหาลูกค้า...': 'Type to search customer...',
    'ค้นหาสินค้า หรือพิมพ์ชื่อ': 'Search product or type name',
    'ค้นหา เลขที่ / ชื่อลูกค้า / โครงการ': 'Search number / customer / project',
    'ค้นหา ชื่อ / รหัส / เลขผู้เสียภาษี': 'Search name / code / tax ID',
    'ค้นหา ชื่อ / รหัส': 'Search name / code',
    'เว้นว่างเพื่อสร้างอัตโนมัติ': 'Leave blank to auto-generate',
    'เอกสารนี้ออกโดยระบบ ThaiBill': 'Generated by EasyBill',
    'เอกสารนี้ออกโดยระบบ EasyBill': 'Generated by EasyBill',
    'พิมพ์เมื่อ': 'Printed at',
    'โปรแกรมบัญชีออนไลน์': 'Online Accounting Software',
    'ระบบเอกสารขายภาษาไทย': 'Online Accounting Software',
    'พิมพ์เอกสาร': 'Print Document',
    'ปิด': 'Close',
    'บัญชีเริ่มต้น': 'Default account',
    'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง': 'Invalid username or password',
    'กรุณาเข้าสู่ระบบก่อนใช้งาน': 'Please sign in to continue',
    'ออกจากระบบเรียบร้อย': 'Signed out',

    # === PDF labels ===
    'ผู้เสนอราคา': 'Issuer',
    'ผู้ออกใบแจ้งหนี้': 'Issuer',
    'ผู้ออกใบกำกับภาษี': 'Issuer',
    'ผู้ส่งสินค้า': 'Sender',
    'ผู้ขนส่ง': 'Carrier',
    'ผู้รับเงิน': 'Receiver',
    'ผู้ตรวจสอบ': 'Checked by',
    'ผู้อนุมัติ (ลูกค้า)': 'Approved by (Customer)',
    'ผู้รับใบแจ้งหนี้': 'Recipient',
    'ผู้รับใบกำกับ': 'Recipient',
    'ผู้ชำระเงิน': 'Payer',
    'รายละเอียดเอกสาร': 'Document Details',

    # === Months — keep ===
}


def get_lang():
    """อ่านภาษาจาก cookie 'lang'"""
    return (request.cookies.get('lang') if request else None) or 'th'


def _(text):
    """แปลข้อความตามภาษาปัจจุบัน — fallback กลับ text เดิมถ้าไม่เจอ"""
    if get_lang() == 'en':
        return EN.get(text, text)
    return text


def register_i18n(app):
    app.jinja_env.globals['_'] = _
    app.jinja_env.globals['get_lang'] = get_lang
