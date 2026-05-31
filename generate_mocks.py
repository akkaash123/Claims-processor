import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

os.makedirs("test_images", exist_ok=True)

def get_font(size, is_bold=False):
    """Attempts to load a standard system font, falls back to default if unavailable."""
    fonts = ["arial.ttf", "Arial.ttf", "Helvetica.ttf", "FreeSans.ttf", "DejaVuSans.ttf"]
    bold_fonts = ["arialbd.ttf", "Arial Bold.ttf", "Helvetica-Bold.ttf", "FreeSansBold.ttf", "DejaVuSans-Bold.ttf"]
    
    target_fonts = bold_fonts if is_bold else fonts
    for font_name in target_fonts:
        try:
            return ImageFont.truetype(font_name, size)
        except IOError:
            continue
    return ImageFont.load_default()

def draw_prescription(draw, patient, doctor, details):
    """Draws a document matching the standard Prescription layout."""
    f_title = get_font(28, is_bold=True)
    f_header = get_font(18)
    f_body = get_font(20)
    f_bold = get_font(20, is_bold=True)

    # Outer Border
    draw.rectangle([20, 20, 780, 980], outline="black", width=3)
    
    # 1. Header Box
    draw.text((40, 40), doctor.upper(), font=f_title, fill='black')
    if "(" in doctor:
        reg_no = doctor.split("(")[1].replace(")", "")
        draw.text((40, 80), f"Reg. No: {reg_no}", font=f_header, fill='#333333')
    draw.text((40, 105), "City Medical Centre, 12 MG Road", font=f_header, fill='#333333')
    draw.line([20, 140, 780, 140], fill="black", width=2)
    
    # 2. Patient Box
    draw.text((40, 155), f"Patient: {patient}", font=f_bold, fill='black')
    date_str = next((d for d in details if "Date:" in d), "Date: 01-Nov-2024")
    draw.text((550, 155), date_str, font=f_body, fill='black')
    draw.line([20, 195, 780, 195], fill="black", width=2)
    
    # 3. Body Box (Diagnosis, Rx, etc.)
    y = 220
    for line in details:
        if "Date:" in line: continue # Already printed
        
        if line.startswith("Diagnosis:") or line.startswith("Rx:"):
            draw.text((40, y), line, font=f_bold, fill='black')
            y += 40
        else:
            # Indent medicines
            draw.text((60, y), f"• {line}", font=f_body, fill='black')
            y += 35

    # 4. Footer
    draw.line([20, 850, 780, 850], fill="black", width=2)
    draw.text((550, 880), "[ Doctor's Signature ]", font=f_header, fill='blue')
    draw.text((550, 920), "[ Clinic Stamp ]", font=f_header, fill='red')

def draw_bill(draw, title, patient, hospital, details):
    """Draws a document matching the standard Hospital/Clinic Invoice layout."""
    f_title = get_font(28, is_bold=True)
    f_header = get_font(18)
    f_body = get_font(20)
    f_bold = get_font(20, is_bold=True)

    # Outer Border
    draw.rectangle([20, 20, 780, 980], outline="black", width=3)
    
    # 1. Header Box
    draw.text((40, 40), hospital.upper(), font=f_title, fill='black')
    draw.text((40, 80), "GSTIN: 29XXXXX1234X1ZX", font=f_header, fill='#333333')
    draw.line([20, 120, 780, 120], fill="black", width=2)
    
    # 2. Bill Info Box
    draw.text((40, 135), f"{title} / RECEIPT", font=f_bold, fill='black')
    date_str = next((d for d in details if "Date:" in d), "Date: 01-Nov-2024")
    draw.text((550, 135), date_str, font=f_body, fill='black')
    draw.line([20, 175, 780, 175], fill="black", width=2)
    
    # 3. Patient Info
    draw.text((40, 190), f"Patient Name: {patient}", font=f_body, fill='black')
    draw.line([20, 230, 780, 230], fill="black", width=2)
    
    # 4. Table Header
    draw.text((40, 250), "DESCRIPTION", font=f_bold, fill='black')
    draw.text((600, 250), "AMOUNT (INR)", font=f_bold, fill='black')
    draw.line([20, 290, 780, 290], fill="black", width=1)
    
    # 5. Table Body
    y = 310
    for line in details:
        if "Date:" in line: continue
        
        if ":" in line:
            item, amount = line.split(":", 1)
            
            # Format totals differently
            if item.strip().upper() in ["TOTAL", "SUBTOTAL"]:
                draw.line([20, y-10, 780, y-10], fill="black", width=1)
                draw.text((400, y), f"{item.strip()}:", font=f_bold, fill='black')
                draw.text((600, y), amount.strip(), font=f_bold, fill='black')
                y += 50
            else:
                draw.text((40, y), item.strip(), font=f_body, fill='black')
                draw.text((600, y), amount.strip(), font=f_body, fill='black')
                y += 40
        else:
            draw.text((40, y), line, font=f_body, fill='black')
            y += 40

    # 6. Footer
    draw.line([20, 850, 780, 850], fill="black", width=2)
    draw.text((40, 880), "Payment Mode: UPI / Card", font=f_header, fill='black')
    draw.text((550, 880), "[ Cashier Stamp ]", font=f_header, fill='red')

def create_document(filename, title, patient, doctor_or_hospital, details, is_blurry=False):
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    # Route to specific layout renderer
    if title == "PRESCRIPTION":
        draw_prescription(draw, patient, doctor_or_hospital, details)
    else:
        draw_bill(draw, title, patient, doctor_or_hospital, details)

    # Apply blur if testing UNREADABLE logic
    if is_blurry:
        img = img.filter(ImageFilter.GaussianBlur(radius=6))

    filepath = os.path.join("test_images", filename)
    img.save(filepath)
    print(f"Generated beautifully formatted: {filepath}")

# --- TEST CASE DATA PAYLOADS ---
documents_to_generate = [
    # TC001: Wrong Document Uploaded
    ("TC001_prescription_1.jpg", "PRESCRIPTION", "Rajesh Kumar", "Dr. Sharma", ["Diagnosis: General Checkup", "Rx: Rest"]),
    ("TC001_prescription_2.jpg", "PRESCRIPTION", "Rajesh Kumar", "Dr. Sharma", ["Diagnosis: Follow up", "Rx: Drink water"]),

    # TC002: Unreadable Document
    ("TC002_prescription.jpg", "PRESCRIPTION", "Sneha Reddy", "Dr. Gupta", ["Diagnosis: Mild Infection", "Rx: Paracetamol 500mg"]),
    ("TC002_blurry_bill.jpg", "PHARMACY INVOICE", "Sneha Reddy", "Apollo Pharmacy", ["Paracetamol: 800", "TOTAL: 800"], True),

    # TC003: Mismatched Patients
    ("TC003_prescription_rajesh.jpg", "PRESCRIPTION", "Rajesh Kumar", "Dr. Arun", ["Diagnosis: Fever", "Rx: Dolo 650"]),
    ("TC003_bill_arjun.jpg", "HOSPITAL BILL", "Arjun Mehta", "City Clinic", ["Consultation: 1500", "TOTAL: 1500"]),

    # TC004: Clean Consultation
    ("TC004_prescription.jpg", "PRESCRIPTION", "Rajesh Kumar", "Dr. Arun Sharma (KA/45678/2015)", ["Date: 2024-11-01", "Diagnosis: Viral Fever", "Rx: Paracetamol 650mg", "Rx: Vitamin C 500mg"]),
    ("TC004_hospital_bill.jpg", "HOSPITAL BILL", "Rajesh Kumar", "City Clinic, Bengaluru", ["Date: 2024-11-01", "Consultation Fee: 1000", "CBC Test: 300", "Dengue NS1 Test: 200", "TOTAL: 1500"]),

    # TC005: Waiting Period (Diabetes)
    ("TC005_prescription.jpg", "PRESCRIPTION", "Vikram Joshi", "Dr. Sunil Mehta (GJ/56789/2014)", ["Date: 2024-10-15", "Diagnosis: Type 2 Diabetes Mellitus", "Rx: Metformin 500mg", "Rx: Glimepiride 1mg"]),
    ("TC005_hospital_bill.jpg", "HOSPITAL BILL", "Vikram Joshi", "City Clinic", ["Date: 2024-10-15", "Consultation: 3000", "TOTAL: 3000"]),

    # TC006: Cosmetic Exclusion (Dental)
    ("TC006_dental_bill.jpg", "HOSPITAL BILL", "Priya Singh", "Smile Dental Clinic", ["Date: 2024-10-15", "Root Canal Treatment: 8000", "Teeth Whitening: 4000", "TOTAL: 12000"]),

    # TC007: Pre-Auth Missing (MRI)
    ("TC007_prescription.jpg", "PRESCRIPTION", "Suresh Patil", "Dr. Venkat Rao (AP/67890/2017)", ["Diagnosis: Suspected Lumbar Disc Herniation", "Advised: MRI Lumbar Spine"]),
    ("TC007_lab_report.jpg", "LABORATORY REPORT", "Suresh Patil", "City Diagnostics", ["MRI Lumbar Spine: 15000", "TOTAL: 15000"]),
    ("TC007_hospital_bill.jpg", "HOSPITAL BILL", "Suresh Patil", "City Diagnostics", ["MRI Lumbar Spine: 15000", "TOTAL: 15000"]),

    # TC008: Limit Exceeded
    ("TC008_prescription.jpg", "PRESCRIPTION", "Amit Verma", "Dr. R. Gupta (DL/34567/2016)", ["Diagnosis: Gastroenteritis", "Rx: Antibiotics", "Rx: Probiotics", "Rx: ORS"]),
    ("TC008_hospital_bill.jpg", "HOSPITAL BILL", "Amit Verma", "Care Hospital", ["Consultation Fee: 2000", "Medicines: 5500", "TOTAL: 7500"]),

    # TC009: Fraud (Multiple Same Day)
    ("TC009_prescription.jpg", "PRESCRIPTION", "Ravi Menon", "Dr. S. Khan", ["Date: 2024-10-30", "Diagnosis: Migraine", "Rx: Painkillers"]),
    ("TC009_hospital_bill.jpg", "HOSPITAL BILL", "Ravi Menon", "Neuro Clinic", ["Date: 2024-10-30", "Consultation: 4800", "TOTAL: 4800"]),

    # TC010: Network Discount Math
    ("TC010_prescription.jpg", "PRESCRIPTION", "Deepak Shah", "Dr. S. Iyer (TN/56789/2013)", ["Date: 2024-11-03", "Diagnosis: Acute Bronchitis", "Rx: Amoxicillin 500mg", "Rx: Salbutamol Inhaler"]),
    ("TC010_hospital_bill.jpg", "HOSPITAL BILL", "Deepak Shah", "Apollo Hospitals", ["Date: 2024-11-03", "Consultation Fee: 1500", "Medicines: 3000", "TOTAL: 4500"]),

    # TC011: Alternative Medicine (AYUSH)
    ("TC011_prescription.jpg", "PRESCRIPTION", "Kavita Nair", "Vaidya T. Krishnan (AYUR/KL/2345/2019)", ["Date: 2024-10-28", "Diagnosis: Chronic Joint Pain", "Advised: Panchakarma Therapy"]),
    ("TC011_hospital_bill.jpg", "HOSPITAL BILL", "Kavita Nair", "Ayur Wellness Centre", ["Date: 2024-10-28", "Panchakarma Therapy (5 sessions): 3000", "Consultation: 1000", "TOTAL: 4000"]),

    # TC012: Obesity Exclusion
    ("TC012_prescription.jpg", "PRESCRIPTION", "Anita Desai", "Dr. P. Banerjee (WB/34567/2015)", ["Date: 2024-10-18", "Diagnosis: Morbid Obesity - BMI 37", "Advised: Bariatric Consultation", "Advised: Customised Diet Plan"]),
    ("TC012_hospital_bill.jpg", "HOSPITAL BILL", "Anita Desai", "Weight Loss Clinic", ["Date: 2024-10-18", "Bariatric Consultation: 3000", "Personalised Diet and Nutrition Program: 5000", "TOTAL: 8000"])
]

print("Generating Beautifully Formatted Test Images...")
for doc in documents_to_generate:
    if len(doc) == 6:
        create_document(doc[0], doc[1], doc[2], doc[3], doc[4], doc[5])
    else:
        create_document(doc[0], doc[1], doc[2], doc[3], doc[4])
        
print("\nSuccess! All 24 realistic test images have been created in the 'test_images' folder.")