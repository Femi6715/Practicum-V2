import mysql.connector
from flask import Flask, render_template, request, jsonify, make_response, send_from_directory, Blueprint
from flask_cors import CORS
import pytesseract
import cv2
import os
from werkzeug.utils import secure_filename
import re
import numpy as np
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
import random
import string
import json  # Needed for converting courses list to JSON
from datetime import datetime
import traceback
from PIL import Image

app = Flask(__name__)
CORS(app)

# Global DB connection (for routes that use it directly)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="62221085",       
    database="mis_gapms"       
)
cursor = db.cursor()

# Helper function to get a fresh DB connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="62221085",
        database="mis_gapms"
    )

# Set Upload Folder and allowed file types
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Set Tesseract OCR Path (For Windows Users)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# List of keywords to check for prerequisite
PREREQUISITE_KEYWORDS = [
    "Programming",          # If a course contains "Programming", no extra prerequisite is needed.
    "Computer Science Basics",
    "Python",
    "BUIS 305"
]

# Define prerequisite keywords
IS_KEYWORDS = ["Information Systems", "INSS", "BUIS", "MIS", "Management Information Systems"]
PROGRAMMING_KEYWORDS = ["Programming", "Python", "Java", "Computer" "C++", "JavaScript", "BUIS 305"]

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Updated OCR Processing Function: supports both image and PDF
def extract_text_from_pdf(file_path):
    """Attempt to extract text using PyPDF2 (works for text-based PDFs)."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        print("DEBUG: PyPDF2 extracted text:", text)
        return text.strip()
    except Exception as e:
        print("Error extracting PDF text with PyPDF2:", e)
        return ""

def process_ocr(file_path):
    print(f"\n=== Starting OCR for file: {file_path} ===")
    ext = file_path.rsplit('.', 1)[1].lower()
    extracted_text = ""
    
    try:
        if ext == "pdf":
            # Try using PyPDF2 first
            extracted_text = extract_text_from_pdf(file_path)
            print(f"PyPDF2 extracted text length: {len(extracted_text)}")
            if len(extracted_text) > 0:
                print("First 200 chars:", extracted_text[:200])
            else:
                print("Warning: PyPDF2 extracted no text")
            
            if not extracted_text:
                print("Falling back to OCR for PDF...")
                # Fall back to OCR
                images = convert_from_path(file_path, dpi=300)
                if images:
                    print(f"Successfully converted PDF to {len(images)} images")
                    image = cv2.cvtColor(np.array(images[0]), cv2.COLOR_RGB2BGR)
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
                    custom_config = r'--oem 3 --psm 6'
                    extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
                    print(f"OCR from PDF image extracted text length: {len(extracted_text)}")
                    if len(extracted_text) > 0:
                        print("First 200 chars:", extracted_text[:200])
                    else:
                        print("Warning: OCR extracted no text from PDF image")
                else:
                    print("Warning: Failed to convert PDF to images")
        else:
            # Process images
            print(f"Processing image file: {file_path}")
            image = cv2.imread(file_path)
            if image is None:
                raise ValueError(f"Could not read the image: {file_path}")
            print(f"Successfully read image: {image.shape}")
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            custom_config = r'--oem 3 --psm 6'
            extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
            print(f"OCR from image extracted text length: {len(extracted_text)}")
            if len(extracted_text) > 0:
                print("First 200 chars:", extracted_text[:200])
            else:
                print("Warning: OCR extracted no text from image")
    
        if not extracted_text.strip():
            print("Warning: No text extracted from file")
            extracted_text = ""
            
        print(f"=== OCR Complete. Text length: {len(extracted_text)} ===\n")
        return extracted_text
        
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        traceback.print_exc()
        raise

def extract_courses(text):
    courses = []

    # Bullet-style: • Programming – Grade: B+
    bullet_pattern = r'•\s*(.*?)\s*[–-]\s*Grade[:：]?\s*([A-F][+-]?)'
    bullet_matches = re.findall(bullet_pattern, text, re.IGNORECASE)
    for name, grade in bullet_matches:
        courses.append({
            "course_name": name.strip(),
            "credits": 3.0,  # Default value when credits aren't listed
            "grade": grade.strip()
        })

    # Classic format: (L) Course Name 3.0 B
    classic_pattern = r'\(L\)\s+(.+?)\s+([\d.]+)\s+([A-F][+-]?)'
    classic_matches = re.findall(classic_pattern, text)
    for name, credits, grade in classic_matches:
        courses.append({
            "course_name": name.strip(),
            "credits": float(credits),
            "grade": grade.strip()
        })

    return courses


def store_courses(application_id, course_list):
    db_conn = get_db_connection()
    cur = db_conn.cursor()
    for course in course_list:
        cur.execute("""
            INSERT INTO courses (application_id, course_name, credits, grade)
            VALUES (%s, %s, %s, %s)
        """, (application_id, course["course_name"], course["credits"], course["grade"]))
    db_conn.commit()
    cur.close()
    db_conn.close()


def extract_transcript_data(text):
    """Extract necessary fields from transcript text with proper error handling"""
    # Initialize variables with default values
    extracted_name = "Unknown"
    extracted_major = "Not Specified"
    extracted_country = "Unknown"
    extracted_degree_level = "Unknown"
    extracted_course = "Unknown"
    prerequisite_required = False
    required_courses = []
    prereq_explanation = ""

    try:
        # Regex patterns to extract needed information
        name_match = re.search(r'(?:Name on Credential|Name):\s*(.*)', text)
        major_match = re.search(r'(?:Major|Degree):\s*(.*)', text)
        country_match = re.search(r'Country or Territory:\s*(.*)', text)
        degree_match = re.search(r'Credential:\s*(.*)', text)
        course_match = re.search(r'Course:\s*(.*)', text)

        # Safely extract values only if matches are found
        if name_match and name_match.group(1):
            extracted_name = name_match.group(1).strip()
        if major_match and major_match.group(1):
            extracted_major = major_match.group(1).strip()
        if country_match and country_match.group(1):
            extracted_country = country_match.group(1).strip()
        if degree_match and degree_match.group(1):
            extracted_degree_level = degree_match.group(1).strip()
        if course_match and course_match.group(1):
            extracted_course = course_match.group(1).strip()

        # Extract courses from the transcript text
        courses = extract_courses(text)
        
        # Check for prerequisite keywords in the extracted courses
        has_is = False
        has_programming = False
        
        for course in courses:
            course_name = course.get('course_name', '').lower()
            if any(keyword.lower() in course_name for keyword in IS_KEYWORDS):
                has_is = True
            if any(keyword.lower() in course_name for keyword in PROGRAMMING_KEYWORDS):
                has_programming = True
            if has_is and has_programming:
                break

        # Determine prerequisite requirements based on the rules
        if has_is and has_programming:
            prerequisite_required = False
            prereq_explanation = "No prerequisites required - found both Information Systems and Programming courses in transcript."
            required_courses = []
        elif not has_is and not has_programming:
            prerequisite_required = True
            prereq_explanation = "Both INSS 400 and INSS 405 are required - no relevant courses found in transcript."
            required_courses = ["INSS 400", "INSS 405"]
        elif has_is and not has_programming:
            prerequisite_required = True
            prereq_explanation = "IS prerequisite required - only IS courses found in transcript."
            required_courses = ["BUIS 360 or INSS 400"]
        else:  # has_programming and not has_is
            prerequisite_required = True
            prereq_explanation = "Programming prerequisite required - only Programming courses found in transcript."
            required_courses = ["BUIS 305", "INSS 450"]

    except Exception as e:
        print(f"Error in extract_transcript_data: {str(e)}")
        # Keep the default values in case of any error
        pass

    return extracted_name, extracted_major, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, required_courses, prereq_explanation

# Function to store transcript data into the transcript_data table
def store_transcript_data(application_id, extracted_text, extracted_name, extracted_major, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, required_courses, prereq_explanation):
    """Store extracted transcript data into the transcript_data table"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First check if record exists
        cursor.execute("SELECT 1 FROM transcript_data WHERE application_id = %s", (application_id,))
        exists = cursor.fetchone()

        if exists:
            # Update existing record
            sql = """
            UPDATE transcript_data 
            SET full_text = %s,
                extracted_name = %s,
                extracted_major = %s,
                extracted_country = %s,
                extracted_degree_level = %s,
                extracted_course = %s,
                prerequisite_required = %s,
                required_courses = %s,
                prereq_explanation = %s
            WHERE application_id = %s
            """
            values = (extracted_text, extracted_name, extracted_major, extracted_country,
                     extracted_degree_level, extracted_course, prerequisite_required, 
                     json.dumps(required_courses), prereq_explanation, application_id)
        else:
            # Insert new record
            sql = """
            INSERT INTO transcript_data 
            (application_id, full_text, extracted_name, extracted_major, extracted_country, 
            extracted_degree_level, extracted_course, prerequisite_required, required_courses, prereq_explanation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (application_id, extracted_text, extracted_name, extracted_major, extracted_country,
                     extracted_degree_level, extracted_course, prerequisite_required, 
                     json.dumps(required_courses), prereq_explanation)
        
        cursor.execute(sql, values)
        conn.commit()
        print(f"Successfully stored transcript data for application {application_id}")

    except Exception as e:
        print(f"Error storing transcript data: {str(e)}")
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Upload and Process File Route (for transcripts)
def generate_application_id():
    return "student" + ''.join(random.choices(string.digits, k=6))

def extract_application_data(text):
    """Extract application data from OCR text"""
    print("\n=== Starting Data Extraction ===")
    
    if not text or not text.strip():
        print("Warning: Empty text provided to extract_application_data")
        return {
            "name": "Unknown",
            "date_of_birth": "Unknown",
            "gender": "Unknown",
            "marital_status": "Unknown",
            "email": "Unknown",
            "phone": "Unknown",
            "address": "Unknown",
            "city": "Unknown",
            "state": "Unknown",
            "zip_code": "Unknown",
            "country": "Unknown",
            "citizenship_status": "Unknown",
            "military_service": "No",
            "field_of_study": "Unknown",
            "program_format": "Unknown",
            "start_semester": "Unknown",
            "start_year": "Unknown",
            "education": {
                "previous_university": "Unknown",
                "degree_earned": "Unknown",
                "degree_major": "Unknown",
                "gpa": "Unknown",
                "credits_earned": "Unknown",
                "attended_from": "Unknown",
                "attended_to": "Unknown"
            }
        }
    
    info = {
        "name": "Unknown",
        "date_of_birth": "Unknown",
        "gender": "Unknown",
        "marital_status": "Unknown",
        "email": "Unknown",
        "phone": "Unknown",
        "address": "Unknown",
        "city": "Unknown",
        "state": "Unknown",
        "zip_code": "Unknown",
        "country": "Unknown",
        "citizenship_status": "Unknown",
        "military_service": "No",
        "field_of_study": "Unknown",
        "program_format": "Unknown",
        "start_semester": "Unknown",
        "start_year": "Unknown",
        "education": {
            "previous_university": "Unknown",
            "degree_earned": "Unknown",
            "degree_major": "Unknown",
            "gpa": "Unknown",
            "credits_earned": "Unknown",
            "attended_from": "Unknown",
            "attended_to": "Unknown"
        }
    }
    
    try:
        # Contact info with improved patterns and logging
        print("\nAttempting to extract email...")
        email_patterns = [
            r'(?:Email|E-mail)\s*(?:Address)?\s*[:：]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'(?:Email|E-mail)[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'(?:Email|E-mail)\s*(?:Address)?[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'(?:Email|E-mail)\s+(?:Address)?[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        # Look for email addresses in the text
        email_found = False
        for pattern in email_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                email = match.group(1).lower()
                print(f"Found email using pattern: {pattern}")
                print(f"Extracted email: {email}")
                # Validate the email format
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    info["email"] = email
                    email_found = True
                    break
                else:
                    print(f"Warning: Found email {email} but it doesn't match the expected format")
        
        if not email_found:
            print("No valid email found in text")
            # Look for any email-like patterns in the text
            potential_emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
            if potential_emails:
                print("Found potential email addresses in text:")
                for email in potential_emails:
                    print(f"- {email}")
        
        # Program Format (Campus) extraction
        campus_pattern = r"Which campus do you plan to attend\?\s*(.*?)(?=\n|$)"
        campus_match = re.search(campus_pattern, text, re.IGNORECASE)
        if campus_match and campus_match.group(1).strip():
            info["program_format"] = campus_match.group(1).strip()
            print(f"Found program format: {info['program_format']}")

        # Field of Study extraction
        study_pattern = r"What do you plan on studying\?\s*(.*?)(?=\n|$)"
        study_match = re.search(study_pattern, text, re.IGNORECASE)
        if study_match and study_match.group(1).strip():
            info["field_of_study"] = study_match.group(1).strip()
            print(f"Found field of study: {info['field_of_study']}")

        # Start Term extraction (split into semester and year)
        term_pattern = r"When do you plan to enroll\?\s*((?:Fall|Spring|Summer)\s*\d{4})(?=\n|$)"
        term_match = re.search(term_pattern, text, re.IGNORECASE)
        if term_match:
            term_parts = term_match.group(1).strip().split()
            if len(term_parts) == 2:
                info["start_semester"] = term_parts[0]
                info["start_year"] = term_parts[1]
                print(f"Found start term: {info['start_semester']} {info['start_year']}")

        # Name extraction (now looking for full name)
        name_patterns = [
            r'(?:Full|Complete)\s*Name\s*[:]?\s*(.*?)(?=\s*(?:Date|Gender|Email|$))',
            r'(?:Name of|Student)\s*Name\s*[:]?\s*(.*?)(?=\s*(?:Date|Gender|Email|$))',
            r'(?:Applicant|Student)\'?s?\s*Name\s*[:]?\s*(.*?)(?=\s*(?:Date|Gender|Email|$))'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                info["name"] = match.group(1).strip()
                print(f"Found name: {info['name']}")
                break
        
        # Date of birth with multiple formats
        dob_patterns = [
            r'(?:Date of Birth|DOB|Birth Date)\s*[:：]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Date of Birth|DOB|Birth Date)\s*[:：]?\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})',
            r'(?:Date of Birth|DOB|Birth Date)\s*[:：]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})'
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["date_of_birth"] = match.group(1)
                print(f"Found DOB: {info['date_of_birth']}")
                break
        
        # Contact info with improved patterns
        phone_pattern = r'(?:Phone|Telephone|Mobile|Cell)\s*(?:Number)?\s*[:：]?\s*([\d\s\-().+]{10,})'
        
        phone_match = re.search(phone_pattern, text, re.IGNORECASE)
        if phone_match:
            # Clean up phone number format
            phone = re.sub(r'[^\d]', '', phone_match.group(1))
            if len(phone) >= 10:
                info["phone"] = f"({phone[:3]}) {phone[3:6]}-{phone[6:10]}"
                print(f"Found phone: {info['phone']}")
        
        # Address info with improved patterns
        address_patterns = {
            'address': r'(?:Street |Mailing )?Address\s*[:：]?\s*(.*?)(?=\s*(?:City|State|ZIP|Postal|$))',
            'city': r'City\s*[:：]?\s*(.*?)(?=\s*(?:State|Province|ZIP|Postal|$))',
            'state': r'(?:State|Province)\s*[:：]?\s*(.*?)(?=\s*(?:ZIP|Postal|$))',
            'zip_code': r'(?:ZIP|Postal)\s*(?:Code)?\s*[:：]?\s*(\d{5}(?:-\d{4})?)',
            'country': r'Country\s*[:：]?\s*(.*?)(?=\s*(?:Citizenship|$))'
        }
        
        for field, pattern in address_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                value = ' '.join(match.group(1).split())
                info[field] = value
                print(f"Found {field}: {info[field]}")
        
        # Citizenship and Military Service
        citizenship_patterns = [
            (r'[☒xX]\s*U\.?S\.?\s*Citizen', 'U.S. Citizen'),
            (r'[☒xX]\s*Permanent\s*Resident', 'Permanent Resident'),
            (r'[☒xX]\s*International\s*Student', 'International Student'),
            (r'Citizenship\s*Status\s*[:：]?\s*(.*?)(?=\s*(?:Military|$))', None)
        ]
        
        for pattern, value in citizenship_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info["citizenship_status"] = value if value else match.group(1).strip()
                print(f"Citizenship Status: {info['citizenship_status']}")
                break
        
        if re.search(r'[☒xX]\s*(?:Yes|Military)', text, re.IGNORECASE):
            info["military_service"] = "Yes"
            print("Military Service: Yes")
        
        # Education info with improved patterns
        edu = info["education"]
        education_patterns = {
            'previous_university': r'(?:University|College|School)\s*(?:Name)?\s*[:：]?\s*(.*?)(?=\s*(?:Degree|Major|GPA|$))',
            'degree_earned': r'(?:Degree|Qualification)\s*(?:Earned)?\s*[:：]?\s*(.*?)(?=\s*(?:Major|GPA|$))',
            'degree_major': r'(?:Major|Field of Study)\s*[:：]?\s*(.*?)(?=\s*(?:GPA|Credits|$))',
            'gpa': r'(?:GPA|Grade Point Average)\s*[:：]?\s*(\d*\.?\d+)',
            'credits_earned': r'(?:Credits?|Hours)\s*(?:Earned|Completed)\s*[:：]?\s*(\d+)'
        }
        
        for field, pattern in education_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                edu[field] = match.group(1).strip()
                print(f"Found {field}: {edu[field]}")
        
        # Program info with improved detection
        if re.search(r'(?:Information Systems|INSS|IS)', text, re.IGNORECASE):
            info["field_of_study"] = "INSS"
        elif re.search(r'(?:Information Assurance|IA|Cybersecurity)', text, re.IGNORECASE):
            info["field_of_study"] = "IA"
        print(f"Field of study: {info['field_of_study']}")
        
        # Format with improved detection
        format_patterns = [
            (r'[☒xX]\s*(?:Main\s*Campus|On[- ]Campus|In[- ]Person)', 'in-person'),
            (r'[☒xX]\s*(?:Online|Remote|Distance)', 'online')
        ]
        for pattern, value in format_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                info["program_format"] = value
                print(f"Program format: {info['program_format']}")
                break
        
        # Semester with improved pattern
        semester_pattern = r'(?:Term|Semester|Start)\s*[:：]?\s*(Fall|Spring|Summer)\s*[of\s]*(\d{4})'
        semester_match = re.search(semester_pattern, text, re.IGNORECASE)
        if semester_match:
            info["start_semester"] = semester_match.group(1)
            info["start_year"] = semester_match.group(2)
            print(f"Found semester: {info['start_semester']} {info['start_year']}")
        
        print("\n=== Extraction Complete ===")
        print("Final extracted data:", json.dumps(info, indent=2))
        
    except Exception as e:
        print(f"Extraction Error: {str(e)}")
        traceback.print_exc()
    
    return info

def store_application_data(application_id, app_data):
    """Store application data in the database"""
    db_conn = get_db_connection()
    cur = db_conn.cursor()
    try:
        # Helper function to safely clean and truncate strings
        def safe_clean(text, max_length=None):
            if text is None:
                return None
            # Convert to string and clean
            text = str(text).strip()
            # Remove any null bytes
            text = text.replace('\x00', '')
            # Replace multiple spaces with single space
            text = ' '.join(text.split())
            # Truncate if max_length is specified
            if max_length and len(text) > max_length:
                print(f"Warning: Truncating value '{text}' to {max_length} characters")
                return text[:max_length]
            return text

        # Clean and validate all string fields
        validated_data = {
            'application_id': safe_clean(application_id, 255),
            'extracted_name': safe_clean(app_data.get("name", "Unknown"), 255),
            'extracted_major': safe_clean(app_data.get("education", {}).get("degree_major", "Unknown"), 255),
            'extracted_country': safe_clean(app_data.get("country", "Unknown"), 255),
            'extracted_degree_level': safe_clean(app_data.get("education", {}).get("degree_earned", "Unknown"), 255),
            'extracted_course': safe_clean("Unknown", 255),
            'extracted_text': safe_clean("", 65535),  # TEXT field
            'extracted_citizenship_status': safe_clean(app_data.get("citizenship_status", "International"), 255),
            'extracted_field_of_study': safe_clean(app_data.get("field_of_study", "Unknown"), 255),
            'extracted_program_format': safe_clean(app_data.get("program_format", "Unknown"), 255),
            'student_status': safe_clean(app_data.get("student_status", "International"), 50),
            'field_of_study': safe_clean(app_data.get("field_of_study", "Unknown"), 50),
            'program_format': safe_clean(app_data.get("program_format", "Unknown"), 50),
            'start_semester': safe_clean(app_data.get("start_semester", "Unknown"), 50),
            'start_year': safe_clean(app_data.get("start_year", "Unknown"), 10),
            'email': safe_clean(app_data.get("email", "Unknown"), 255),
            'phone': safe_clean(app_data.get("phone", "Unknown"), 50),
            'address': safe_clean(app_data.get("address", "Unknown")),  # TEXT field
            'city': safe_clean(app_data.get("city", "Unknown"), 100),
            'state': safe_clean(app_data.get("state", "Unknown"), 100),
            'zip_code': safe_clean(app_data.get("zip_code", "Unknown"), 20),
            'country': safe_clean(app_data.get("country", "Unknown"), 100),
            'citizen_type': safe_clean(app_data.get("citizenship_status", "International"), 50),
            'university': safe_clean(app_data.get("education", {}).get("previous_university", "Unknown"), 255),
            'degree': safe_clean(app_data.get("education", {}).get("degree_earned", "Unknown"), 100),
            'major': safe_clean(app_data.get("education", {}).get("degree_major", "Unknown"), 255),
            'campus': safe_clean(app_data.get("plans", {}).get("campus", "Unknown"), 50),
            'program': safe_clean(app_data.get("plans", {}).get("intended_major", "Unknown"), 255),
            'enrollment_semester': safe_clean(app_data.get("plans", {}).get("enrollment_term", "Unknown"), 50),
            'residency_status': safe_clean(app_data.get("student_status", "International"), 100)
        }

        # Print the cleaned data for debugging
        print("\nValidated data:")
        for key, value in validated_data.items():
            print(f"{key}: {value}")

        cur.execute("""
            INSERT INTO application_data (
                    application_id,
                    extracted_name,
                    extracted_major,
                    extracted_country,
                    extracted_degree_level,
                    extracted_course,
                    prerequisite_required,
                    extracted_text,
                    extracted_citizenship_status,
                    extracted_field_of_study,
                    extracted_program_format,
                    student_status,
                    field_of_study,
                    program_format,
                    start_semester,
                    start_year,
                    email,
                    phone,
                    address,
                    city,
                    state,
                    zip_code,
                    country,
                    is_us_resident,
                    citizen_type,
                    military_service,
                    university,
                    degree,
                    major,
                    gpa,
                    campus,
                    program,
                    enrollment_semester,
                    residency_status,
                    is_international,
                    age
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            validated_data['application_id'],
            validated_data['extracted_name'],
            validated_data['extracted_major'],
            validated_data['extracted_country'],
            validated_data['extracted_degree_level'],
            validated_data['extracted_course'],
            0,  # prerequisite_required
            validated_data['extracted_text'],
            validated_data['extracted_citizenship_status'],
            validated_data['extracted_field_of_study'],
            validated_data['extracted_program_format'],
            validated_data['student_status'],
            validated_data['field_of_study'],
            validated_data['program_format'],
            validated_data['start_semester'],
            validated_data['start_year'],
            validated_data['email'],
            validated_data['phone'],
            validated_data['address'],
            validated_data['city'],
            validated_data['state'],
            validated_data['zip_code'],
            validated_data['country'],
            1 if app_data.get("citizenship_status") == "U.S. Citizen" else 0,
            validated_data['citizen_type'],
            1 if app_data.get("military_service") == "Yes" else 0,
            validated_data['university'],
            validated_data['degree'],
            validated_data['major'],
            float(app_data.get("education", {}).get("gpa", "0.0")) if app_data.get("education", {}).get("gpa") != "Unknown" else None,
            validated_data['campus'],
            validated_data['program'],
            validated_data['enrollment_semester'],
            validated_data['residency_status'],
            1 if app_data.get("student_status") == "international" else 0,
            int(app_data.get("age", 0)) if app_data.get("age") != "Unknown" else None
        ))
        db_conn.commit()
        print("\n✅ Successfully stored application data")
    except Exception as e:
        print("\n❌ Failed to insert application data:", str(e))
        print("Attempted values:", validated_data)
        raise
    finally:
        cur.close()
        db_conn.close()

@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        try:
            if 'transcript' not in request.files or 'application_data' not in request.files:
                return jsonify({"error": "Both transcript and application data files are required"}), 400
                
            transcript_file = request.files['transcript']
            application_file = request.files['application_data']
            
            if transcript_file.filename == '' or application_file.filename == '':
                return jsonify({"error": "No selected files"}), 400
                
            if not all(allowed_file(f.filename) for f in [transcript_file, application_file]):
                return jsonify({"error": "Invalid file type"}), 400
                
            # Process transcript first to extract name
            transcript_filename = secure_filename(transcript_file.filename)
            transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
            transcript_file.save(transcript_path)
            
            # Extract text from transcript
            try:
                transcript_text = process_ocr(transcript_path)
                extracted_name, extracted_major, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, required_courses, prereq_explanation = extract_transcript_data(transcript_text)
            except Exception as e:
                print(f"OCR processing error: {str(e)}")
                return jsonify({"error": f"OCR processing failed: {str(e)}"}), 500
            
            # Check if student already exists
            db_conn = None
            cur = None
            try:
                db_conn = get_db_connection()
                cur = db_conn.cursor()
                cur.execute("SELECT application_id FROM transcript_data WHERE extracted_name = %s", (extracted_name,))
                existing_student = cur.fetchone()
                if existing_student:
                    return jsonify({"error": f"Student '{extracted_name}' already exists in the system with application ID: {existing_student[0]}"}), 400
            finally:
                if cur:
                    cur.close()
                if db_conn:
                    db_conn.close()
            
            # Generate a new application ID
            application_id = generate_application_id()
            
            # Save application file
            application_filename = secure_filename(application_file.filename)
            application_path = os.path.join(app.config['UPLOAD_FOLDER'], application_filename)
            application_file.save(application_path)
            
            # Process application data
            try:
                application_text = process_ocr(application_path)
                application_data = extract_application_data(application_text)
            except Exception as e:
                print(f"OCR processing error: {str(e)}")
                return jsonify({"error": f"OCR processing failed: {str(e)}"}), 500
            
            # First, ensure the application_id exists in application_records
            db_conn = get_db_connection()
            cur = db_conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO application_records (application_id)
                    VALUES (%s)
                """, (application_id,))
                db_conn.commit()
            except Exception as e:
                print(f"Database error inserting application record: {str(e)}")
                return jsonify({"error": f"Database error: {str(e)}"}), 500
            finally:
                cur.close()
                db_conn.close()
            
            # Store file information in database
            db_conn = get_db_connection()
            cur = db_conn.cursor()
            try:
                # Insert transcript file
                cur.execute("""
                    INSERT INTO files (application_id, filename, file_type)
                    VALUES (%s, %s, %s)
                """, (application_id, transcript_filename, 'transcript'))
                
                # Insert application file
                cur.execute("""
                    INSERT INTO files (application_id, filename, file_type)
                    VALUES (%s, %s, %s)
                """, (application_id, application_filename, 'application'))
                
                db_conn.commit()
            except Exception as e:
                print(f"Database error storing file information: {str(e)}")
                return jsonify({"error": f"Database error: {str(e)}"}), 500
            finally:
                cur.close()
                db_conn.close()
            
            # Extract courses from transcript
            courses = extract_courses(transcript_text)
            
            # Store all the data
            store_courses(application_id, courses)
            store_transcript_data(
                application_id,
                transcript_text,
                extracted_name,
                extracted_major,
                extracted_country,
                extracted_degree_level,
                extracted_course,
                prerequisite_required,
                required_courses,
                prereq_explanation
            )
            store_application_data(application_id, application_data)

            # Prepare student info for response
            student_info = {
                "extracted_name": extracted_name,
                "extracted_major": extracted_major,
                "extracted_country": extracted_country,
                "extracted_degree_level": extracted_degree_level,
                "extracted_course": extracted_course,
                "student_status": application_data.get("student_status", "Unknown"),
                "field_of_study": application_data.get("field_of_study", "Unknown"),
                "program_format": application_data.get("program_format", "Unknown"),
                "start_semester": application_data.get("start_semester", "Unknown"),
                "start_year": application_data.get("start_year", "Unknown"),
                "address": application_data.get("address", "Unknown"),
                "city": application_data.get("city", "Unknown"),
                "state": application_data.get("state", "Unknown"),
                "zip_code": application_data.get("zip_code", "Unknown"),
                "country": application_data.get("country", "Unknown"),
                "military_service": application_data.get("military_service", "No"),
                "citizen_type": application_data.get("citizen_type", "Unknown")
            }

            return jsonify({
                "message": "Documents processed successfully",
                "application_id": application_id,
                "student_info": student_info,
                "extracted_text": transcript_text,
                "prerequisite_required": prerequisite_required,
                "courses_found": len(courses)
            })
            
        except Exception as e:
            print(f"Error processing files: {str(e)}")
            return jsonify({"error": f"Processing failed: {str(e)}"}), 500

    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Other Routes remain unchanged
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/review')
def review_applications():
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        db_conn = get_db_connection()
        cur = db_conn.cursor(dictionary=True)
        query = """
            SELECT transcript_id, extracted_name, extracted_country, extracted_degree_level,
                   extracted_course, prerequisite_required, details
            FROM transcript_data
        """
        cur.execute(query)
        transcripts = cur.fetchall()
        cur.close()
        db_conn.close()
        return jsonify(transcripts)
    return render_template('review.html')

@app.route('/manage-decisions')
def manage_decisions():
    return render_template('manage_decisions.html')

@app.route('/generate-reports')
def generate_reports():
    return render_template('generate_reports.html')

@app.route('/query-students')
def query_students():
    return render_template('query_students.html')

@app.route('/help')
def help_page():
    return render_template('help.html')

@app.route('/signin')
def signin():
    return render_template('signin.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        full_name = data.get('full_name')
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        role = 'Applicant'
        gender = data.get('gender')
        age = data.get('age')
        nationality = data.get('nationality')
        residency_status = data.get('residency_status')
        try:
            cursor.execute("""
                INSERT INTO users (full_name, email, username, password, role)
                VALUES (%s, %s, %s, %s, %s)
            """, (full_name, email, username, password, role))
            db.commit()
            user_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO student_demographics (user_id, gender, age, nationality, residency_status)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, gender, age, nationality, residency_status))
            db.commit()
            return jsonify({"message": "Registration Successful", "user_id": user_id}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return render_template('register.html')

@app.route('/get-all-students')
def get_all_students():
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    query = "SELECT full_name, email, status FROM users"
    cur.execute(query)
    students = cur.fetchall()
    cur.close()
    db_conn.close()
    return jsonify(students)

@app.route('/get-transcript-data')
def get_transcript_data():
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    query = """
        SELECT transcript_id, extracted_name, extracted_country, extracted_degree_level,
               extracted_course, prerequisite_required, details
        FROM transcript_data
    """
    cur.execute(query)
    transcripts = cur.fetchall()
    cur.close()
    db_conn.close()
    return jsonify(transcripts)

@app.route('/update-transcript/<int:transcript_id>', methods=['POST'])
def update_transcript(transcript_id):
    data = request.get_json()
    new_name = data.get('extracted_name')
    new_country = data.get('extracted_country')
    new_degree = data.get('extracted_degree_level')
    new_course = data.get('extracted_course')
    new_details = data.get('details')
    new_prereq = data.get('prerequisite_required')
    if None in [new_name, new_country, new_degree, new_course, new_details, new_prereq]:
        return jsonify({"error": "Missing required fields"}), 400
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor()
        query = """
            UPDATE transcript_data
            SET extracted_name = %s,
                extracted_country = %s,
                extracted_degree_level = %s,
                extracted_course = %s,
                details = %s,
                prerequisite_required = %s
            WHERE transcript_id = %s
        """
        cur.execute(query, (new_name, new_country, new_degree, new_course, new_details, new_prereq, transcript_id))
        db_conn.commit()
        cur.close()
        db_conn.close()
        return jsonify({"message": "Transcript updated successfully", "transcript_id": transcript_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete-transcript/<int:transcript_id>', methods=['DELETE'])
def delete_transcript(transcript_id):
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor()
        query = "DELETE FROM transcript_data WHERE transcript_id = %s"
        cur.execute(query, (transcript_id,))
        db_conn.commit()
        cur.close()
        db_conn.close()
        return jsonify({"message": "Transcript deleted successfully", "transcript_id": transcript_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get-report-data', methods=['GET'])
def get_report_data():
    report_type = request.args.get('report_type')
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    if report_type == "StudentList":
        query = "SELECT extracted_name, extracted_course, extracted_country FROM transcript_data"
    elif report_type == "PrerequisiteRequired":
        query = "SELECT extracted_name, extracted_course, extracted_country FROM transcript_data WHERE prerequisite_required = TRUE"
    elif report_type == "PrerequisiteNotRequired":
        query = "SELECT extracted_name, extracted_course, extracted_country FROM transcript_data WHERE prerequisite_required = FALSE"
    else:
        cur.close()
        db_conn.close()
        return jsonify({"error": "Invalid report type"}), 400
    cur.execute(query)
    report_data = cur.fetchall()
    cur.close()
    db_conn.close()
    return jsonify(report_data)

@app.route('/get-admitted-students', methods=['GET'])
def get_admitted_students():
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                td.application_id,
                COALESCE(td.extracted_name, 'Unknown') as extracted_name,
                COALESCE(td.extracted_major, 'Not Specified') as extracted_major
            FROM transcript_data td
            WHERE td.application_id IS NOT NULL
        """
        cur.execute(query)
        results = cur.fetchall()
        
        # If no results found in transcript_data, try getting from application_data
        if not results:
            query = """
                SELECT 
                    application_id,
                    COALESCE(extracted_name, 'Unknown') as extracted_name,
                    COALESCE(extracted_major, 'Not Specified') as extracted_major
                FROM application_data
                WHERE application_id IS NOT NULL
            """
            cur.execute(query)
            results = cur.fetchall()
        
        print(f"Found {len(results)} students")
        return jsonify(results)
    except Exception as e:
        print(f"Error getting admitted students: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        db_conn.close()

@app.route('/update-keywords', methods=['POST'])
def update_keywords():
    global PREREQUISITE_KEYWORDS
    data = request.get_json()
    new_keywords = data.get('keywords')
    if not new_keywords:
        return jsonify({"error": "No keywords provided"}), 400
    # Expecting a comma-separated string
    if isinstance(new_keywords, str):
        new_keywords_list = [kw.strip() for kw in new_keywords.split(',') if kw.strip()]
    else:
        return jsonify({"error": "Invalid format for keywords"}), 400
    PREREQUISITE_KEYWORDS = new_keywords_list
    return jsonify({"message": "Keywords updated successfully", "keywords": PREREQUISITE_KEYWORDS})

@app.route('/student-details/<application_id>')
def student_details(application_id):
    # You might fetch additional details if needed here
    return render_template('student_details.html', application_id=application_id)

@app.route('/update-course/<int:course_id>', methods=['POST'])
def update_course(course_id):
    data = request.get_json()
    try:
        # Update course details in the database
        db_conn = get_db_connection()
        cur = db_conn.cursor()
        cur.execute("""
            UPDATE courses SET 
                course_name = %s, 
                credits = %s, 
                grade = %s
            WHERE course_id = %s
        """, (data['courseName'], data['credits'], data['grade'], course_id))
        db_conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        db_conn.close()

@app.route('/get-courses/<application_id>', methods=['GET'])
def get_courses(application_id):
    print(f"\n=== Getting courses for application_id: {application_id} ===")
    db_conn = None
    cur = None
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor(dictionary=True)
        
        # First check if the application exists
        cur.execute("SELECT 1 FROM application_records WHERE application_id = %s", (application_id,))
        if not cur.fetchone():
            print(f"❌ Application ID {application_id} not found in application_records")
            return jsonify([])
        
        # Check if there are any courses
        cur.execute("SELECT COUNT(*) as count FROM courses WHERE application_id = %s", (application_id,))
        count = cur.fetchone()['count']
        print(f"Found {count} courses for application {application_id}")
        
        if count == 0:
            print("No courses found for this application")
            return jsonify([])
            
        # Get courses from database
        query = """
            SELECT 
                course_id,
                COALESCE(course_name, 'Unknown') as course_name,
                COALESCE(credits, 0.0) as credits,
                COALESCE(grade, 'N/A') as grade
            FROM courses 
            WHERE application_id = %s
            ORDER BY course_id
        """
        cur.execute(query, (application_id,))
        courses = cur.fetchall()
        
        print("Returning courses:", courses)
        return jsonify(courses)
        
    except Exception as e:
        print(f"❌ Error getting courses: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        if cur:
            cur.close()
        if db_conn:
            db_conn.close()
            print("Database connection closed")

@app.route('/delete-course/<int:course_id>', methods=['POST'])
def delete_course(course_id):
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor()
        cur.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        db_conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'db_conn' in locals() and db_conn:
            db_conn.close()

@app.route('/test-delete/<int:id>', methods=['GET'])
def test_delete(id):
    return jsonify({'message': f'Test delete endpoint working for ID: {id}'})

# Create a table for prerequisite courses
@app.route('/create-prerequisites-table', methods=['GET'])
def create_prerequisites_table():
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prerequisites (
                id INT AUTO_INCREMENT PRIMARY KEY,
                application_id VARCHAR(255) NOT NULL,
                prerequisite_id INT NOT NULL,
                prerequisite_name VARCHAR(255) NOT NULL,
                required BOOLEAN DEFAULT TRUE,
                term VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_prerequisite (application_id, prerequisite_id)
            )
        """)
        db_conn.commit()
        return jsonify({'success': True, 'message': 'Prerequisites table created successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'db_conn' in locals() and db_conn:
            db_conn.close()

# Get prerequisites for a student
@app.route('/get-prerequisites/<application_id>', methods=['GET'])
def get_prerequisites(application_id):
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor(dictionary=True)
        cur.execute("""
            SELECT prerequisite_id as id, prerequisite_name as name
            FROM prerequisites
            WHERE application_id = %s
        """, (application_id,))
        prerequisites = cur.fetchall()
        return jsonify({'prerequisites': prerequisites}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'db_conn' in locals() and db_conn:
            db_conn.close()

# Save prerequisites for a student (with required status)
@app.route('/save-prerequisites/<application_id>', methods=['POST'])
def save_prerequisites(application_id):
    try:
        data = request.json
        prerequisites = data.get('prerequisites', [])
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First delete existing prerequisites for this application
        cursor.execute('''
            DELETE FROM prerequisites 
            WHERE application_id = %s
        ''', (application_id,))
        
        # Insert new prerequisites
        for prereq in prerequisites:
            course_id = prereq['id']
            required = prereq.get('required', True)
            term = prereq.get('term', 'Fall')
            prereq_name = None
            
            # Find the course name from available prerequisites
            for available_prereq in [
                {"id": 1, "name": "INSS 500 Introduction to Information Systems"},
                {"id": 2, "name": "INSS 505 Object Oriented Programming"},
                {"id": 3, "name": "INSS 515 Principles & Practices of Information Systems"}
            ]:
                if available_prereq["id"] == course_id:
                    prereq_name = available_prereq["name"]
                    break
                    
            if prereq_name is None:
                continue
                
            # Insert the prerequisite with all fields
            cursor.execute('''
                INSERT INTO prerequisites 
                (application_id, prerequisite_id, prerequisite_name, required, term)
                VALUES (%s, %s, %s, %s, %s)
            ''', (application_id, course_id, prereq_name, required, term))
            
        conn.commit()
        return jsonify({"success": True, "message": "Prerequisites saved successfully"}), 200
        
    except Exception as e:
        print(f"Error saving prerequisites: {e}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({"error": str(e)}), 500
        
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/get-student-info/<application_id>', methods=['GET'])
def get_student_info(application_id):
    print(f"\n=== Getting student info for application_id: {application_id} ===")
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    try:
        # First check if the application_id exists
        cur.execute("SELECT 1 FROM application_records WHERE application_id = %s", (application_id,))
        if not cur.fetchone():
            print(f"❌ Application ID {application_id} not found in application_records")
            return jsonify({
                "extracted_name": "Unknown Student",
                "extracted_major": "Unknown",
                "citizenship": "International",
                "fieldOfStudy": "Unknown",
                "programFormat": "Unknown",
                "startSemester": "Unknown",
                "startYear": "Unknown",
                "email": "Unknown",
                "student_status": "International"
            })

        # If application_id exists, get the student info
        query = """
            SELECT 
                COALESCE(td.extracted_name, 'Unknown Student') as extracted_name,
                COALESCE(td.extracted_major, 'Unknown') as extracted_major,
                COALESCE(ad.extracted_citizenship_status, 'International') as citizenship,
                COALESCE(ad.field_of_study, 'Unknown') as fieldOfStudy,
                COALESCE(ad.program_format, 'Unknown') as programFormat,
                COALESCE(ad.start_semester, 'Unknown') as startSemester,
                COALESCE(ad.start_year, 'Unknown') as startYear,
                COALESCE(ad.email, 'Unknown') as email,
                COALESCE(ad.student_status, 'International') as student_status
            FROM application_records ar
            LEFT JOIN transcript_data td ON ar.application_id = td.application_id
            LEFT JOIN application_data ad ON ar.application_id = ad.application_id
            WHERE ar.application_id = %s
        """
        cur.execute(query, (application_id,))
        result = cur.fetchone()
        
        if not result:
            print(f"❌ No data found for application_id {application_id}")
            return jsonify({
                "extracted_name": "Unknown Student",
                "extracted_major": "Unknown",
                "citizenship": "International",
                "fieldOfStudy": "Unknown",
                "programFormat": "Unknown",
                "startSemester": "Unknown",
                "startYear": "Unknown",
                "email": "Unknown",
                "student_status": "International"
            })
            
        print(f"✅ Found student data: {result}")
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Error in get_student_info: {str(e)}")
        return jsonify({
            "extracted_name": "Unknown Student",
            "extracted_major": "Unknown",
            "citizenship": "International",
            "fieldOfStudy": "Unknown",
            "programFormat": "Unknown",
            "startSemester": "Unknown",
            "startYear": "Unknown",
            "email": "Unknown",
            "student_status": "International"
        })
    finally:
        cur.close()
        db_conn.close()

# Route to display the prerequisite print page
@app.route('/prerequisite-print/<application_id>')
def prerequisite_print(application_id):
    return render_template('prerequisite_print.html')

# API endpoint to get prerequisite data for printing
@app.route('/get-prerequisite-data/<application_id>')
def get_prerequisite_data(application_id):
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor(dictionary=True)
        cur.execute("""
            SELECT extracted_name, extracted_major
            FROM transcript_data
            WHERE application_id = %s
        """, (application_id,))
        student_info = cur.fetchone()
        cur.execute("""
            SELECT prerequisite_id as id, prerequisite_name as name
            FROM prerequisites
            WHERE application_id = %s
        """, (application_id,))
        prerequisites = cur.fetchall()
        if not student_info:
            student_name = "Unknown Student"
            student_id = "N/A"
        else:
            student_name = student_info['extracted_name'] or "Unknown Student"
            student_id = "BSU" + application_id[-6:] if application_id.startswith("student") else "N/A"
        return jsonify({
            "studentName": student_name,
            "studentId": student_id,
            "applicationId": application_id,
            "prerequisites": prerequisites or []
        })
    except Exception as e:
        print(f"Error getting prerequisite data: {e}")
        return jsonify({"error": "Failed to fetch prerequisite data."}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'db_conn' in locals():
            db_conn.close()

# General prerequisite status endpoint (kept as the single definition)
@app.route('/get-prerequisite-status/<application_id>', methods=['GET'])
def get_prerequisite_status(application_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # First check if the application_id exists and get the courses
        cursor.execute("""
            SELECT c.course_name 
            FROM courses c
            WHERE c.application_id = %s
        """, (application_id,))
        
        courses = cursor.fetchall()
        cursor.close()  # Close cursor after reading results
        
        if not courses:
            return jsonify({
                "required": True,
                "explanation": "No courses found. Prerequisites required by default.",
                "required_courses": ["INSS 400", "INSS 405"]
            }), 200

        # Check for IS and Programming keywords in the course names
        has_is = False
        has_programming = False
        
        for course in courses:
            course_name = course['course_name'].lower()
            if any(keyword.lower() in course_name for keyword in IS_KEYWORDS):
                has_is = True
            if any(keyword.lower() in course_name for keyword in PROGRAMMING_KEYWORDS):
                has_programming = True
            if has_is and has_programming:
                break
        
        if has_is and has_programming:
            return jsonify({
                "required": False,
                "explanation": "No prerequisites required - found both Information Systems and Programming courses in transcript.",
                "required_courses": []
            }), 200
        elif not has_is and not has_programming:
            return jsonify({
                "required": True,
                "explanation": "Both INSS 400 and INSS 405 are required - no relevant courses found in transcript.",
                "required_courses": ["INSS 400", "INSS 405"]
            }), 200
        elif has_is and not has_programming:
            return jsonify({
                "required": True,
                "explanation": "IS prerequisite required - only IS courses found in transcript.",
                "required_courses": ["BUIS 360 or INSS 400"]
            }), 200
        else:  # has_programming and not has_is
            return jsonify({
                "required": True,
                "explanation": "Programming prerequisite required - only Programming courses found in transcript.",
                "required_courses": ["BUIS 360 or INSS 400"]
            }), 200
            
    except Exception as e:
        print(f"Error getting prerequisite status: {e}")
        return jsonify({
            "required": True,
            "explanation": "Error evaluating prerequisites. Defaulting to required.",
            "required_courses": ["INSS 400", "INSS 405"]
        }), 200
    finally:
        if 'conn' in locals() and conn:
            conn.close()

# Endpoint to get prerequisite status for a specific course in an application
@app.route('/get-prerequisite-status/<application_id>/<course_id>', methods=['GET'])
def get_course_prerequisite_status(application_id, course_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('''
            SELECT required FROM prerequisites 
            WHERE application_id = %s AND prerequisite_id = %s
        ''', (application_id, course_id))
        result = cursor.fetchone()
        if result is None:
            cursor.execute('''
                SELECT prerequisite FROM applications 
                WHERE application_id = %s
            ''', (application_id,))
            app_result = cursor.fetchone()
            cursor.close()
            conn.close()
            if app_result is None:
                return jsonify({"required": True}), 200  # Default to required if no record found
            return jsonify({"required": bool(app_result['prerequisite'])}), 200
        cursor.close()
        conn.close()
        return jsonify({"required": bool(result['required'])}), 200
    except Exception as e:
        print(f"Error getting course prerequisite status: {e}")
        return jsonify({"error": str(e)}), 500


#new
# Add these new functions to your app.py

def extract_student_info(text):
    """Extract student biodata from application form text"""
    info = {
        "name": "Unknown",
        "dob": "Unknown",
        "email": "Unknown",
        "phone": "Unknown",
        "address": "Unknown"
    }
    
    # Name patterns
    name_patterns = [
        r"Full Name[:]?\s*(.*)",
        r"Name of Applicant[:]?\s*(.*)",
        r"Applicant[']?s Name[:]?\s*(.*)"
    ]
    
    # DOB patterns
    dob_patterns = [
        r"Date of Birth[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"DOB[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Birth Date[:]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]
    
    # Email patterns
    email_patterns = [
        r"Email (?:Address)?[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"E-mail[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    ]
    
    # Phone patterns
    phone_patterns = [
        r"Phone (?:Number)?[:]?\s*([+\d\s\-()]{7,})",
        r"Telephone[:]?\s*([+\d\s\-()]{7,})",
        r"Mobile[:]?\s*([+\d\s\-()]{7,})"
    ]
    
    # Address patterns (multi-line)
    address_patterns = [
        r"Address[:]?\s*((?:.+\n)+?(?=\w+[:]?|$))",
        r"Permanent Address[:]?\s*((?:.+\n)+?(?=\w+[:]?|$))"
    ]
    
    # Search for each field
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info["name"] = match.group(1).strip()
            break
            
    for pattern in dob_patterns:
        match = re.search(pattern, text)
        if match:
            info["dob"] = match.group(1).strip()
            break
            
    for pattern in email_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            info["email"] = match.group(1).strip()
            break
            
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            info["phone"] = match.group(1).strip()
            break
            
    for pattern in address_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            info["address"] = " ".join(line.strip() for line in match.group(1).split("\n"))
            break
            
    return info

@app.route('/upload-documents', methods=['POST'])
def upload_documents():
    if 'application_form' not in request.files or 'transcript' not in request.files:
        return jsonify({"error": "Both application form and transcript are required"}), 400
        
    app_form = request.files['application_form']
    transcript = request.files['transcript']
    
    if app_form.filename == '' or transcript.filename == '':
        return jsonify({"error": "No selected files"}), 400
        
    # Process application form
    if app_form and allowed_file(app_form.filename):
        app_form_filename = secure_filename(app_form.filename)
        app_form_path = os.path.join(app.config['UPLOAD_FOLDER'], app_form_filename)
        app_form.save(app_form_path)
        
        try:
            # Extract text from application form
            app_form_text = process_ocr(app_form_path)
            student_info = extract_student_info(app_form_text)
            app_data = extract_application_data(app_form_text)
        except Exception as e:
            return jsonify({"error": f"Application form processing failed: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid application form file type"}), 400
        
    # Process transcript
    if transcript and allowed_file(transcript.filename):
        transcript_filename = secure_filename(transcript.filename)
        transcript_path = os.path.join(app.config['UPLOAD_FOLDER'], transcript_filename)
        transcript.save(transcript_path)
        
        try:
            # Extract text from transcript
            print("\n=== Processing Transcript ===")
            extracted_text = process_ocr(transcript_path)
            print(f"Extracted text length: {len(extracted_text)}")
            
            # Extract transcript data
            extracted_name, extracted_major, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, required_courses, prereq_explanation = extract_transcript_data(extracted_text)
            
            # Extract and store courses
            print("\nExtracting courses from transcript...")
            courses = extract_courses(extracted_text)
            print(f"Found {len(courses)} courses")
            
            # Generate application ID
            application_id = generate_application_id()
            
            # Store all data
            try:
                # First store the application record
                db_conn = get_db_connection()
                cur = db_conn.cursor()
                cur.execute("""
                    INSERT INTO application_records (application_id, transcript_file, application_file)
                    VALUES (%s, %s, %s)
                """, (application_id, transcript_filename, app_form_filename))
                db_conn.commit()
                cur.close()
                db_conn.close()
                
                # Store transcript data
                store_transcript_data(
                    application_id,
                    extracted_text,
                    extracted_name,
                    extracted_major,
                    extracted_country,
                    extracted_degree_level,
                    extracted_course,
                    prerequisite_required,
                    required_courses,
                    prereq_explanation
                )
                
                # Store application data
                store_application_data(application_id, app_data)
                
                # Store courses
                if courses:
                    print(f"\nStoring {len(courses)} courses...")
                    store_courses(application_id, courses)
                    print("Courses stored successfully")
                
                return jsonify({
                    "success": True,
                    "message": "Documents processed successfully",
                    "application_id": application_id,
                    "student_info": student_info,
                    "courses_found": len(courses),
                    "prerequisite_required": prerequisite_required
                })
                
            except Exception as e:
                print(f"Error storing data: {str(e)}")
                return jsonify({"error": f"Failed to store data: {str(e)}"}), 500
                
        except Exception as e:
            print(f"Error processing transcript: {str(e)}")
            return jsonify({"error": f"Transcript processing failed: {str(e)}"}), 500
    else:
        return jsonify({"error": "Invalid transcript file type"}), 400

def create_application_data_table():
    """Create the application_data table if it doesn't exist"""
    db_conn = get_db_connection()
    cur = db_conn.cursor()
    try:
        # First, add file_type column to files table if it doesn't exist
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'files' 
            AND column_name = 'file_type'
        """)
        if cur.fetchone()[0] == 0:
            cur.execute("""
                ALTER TABLE files 
                ADD COLUMN file_type VARCHAR(50) AFTER filename
            """)
            print("Added file_type column to files table")

        # Create application_data table with increased column lengths
        cur.execute("""
            CREATE TABLE IF NOT EXISTS application_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                application_id VARCHAR(255) NOT NULL,
                student_status VARCHAR(100),
                field_of_study VARCHAR(255),
                program_format VARCHAR(100),
                start_semester VARCHAR(50),
                start_year VARCHAR(4),
                extracted_citizenship_status VARCHAR(100),
                extracted_field_of_study VARCHAR(255),
                extracted_program_format VARCHAR(100),
                email VARCHAR(255),
                phone VARCHAR(50),
                address TEXT,
                city VARCHAR(100),
                state VARCHAR(100),
                zip_code VARCHAR(20),
                country VARCHAR(255),
                is_us_resident BOOLEAN,
                citizen_type VARCHAR(100),
                military_service BOOLEAN,
                university VARCHAR(255),
                degree VARCHAR(255),
                major VARCHAR(255),
                gpa DECIMAL(3,2),
                campus VARCHAR(100),
                program VARCHAR(255),
                enrollment_semester VARCHAR(50),
                residency_status VARCHAR(100),
                is_international BOOLEAN,
                age INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES files(application_id)
            )
        """)

        # Also update the transcript_data table if it exists
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'transcript_data'
        """)
        if cur.fetchone()[0] > 0:
            try:
                cur.execute("""
                    ALTER TABLE transcript_data
                    MODIFY COLUMN extracted_name VARCHAR(255),
                    MODIFY COLUMN extracted_major VARCHAR(255),
                    MODIFY COLUMN extracted_country VARCHAR(255),
                    MODIFY COLUMN extracted_degree_level VARCHAR(255),
                    MODIFY COLUMN extracted_course VARCHAR(255)
                """)
                print("Updated transcript_data column lengths")
            except Exception as e:
                print(f"Note: Could not modify transcript_data columns: {e}")

        db_conn.commit()
        print("Database tables updated successfully")
    except Exception as e:
        print("Error updating tables:", e)
        raise
    finally:
        cur.close()
        db_conn.close()

def check_table_structure():
    """Check and print the current structure of relevant tables"""
    db_conn = get_db_connection()
    cur = db_conn.cursor()
    try:
        # Check transcript_data table
        cur.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'transcript_data'
            ORDER BY ORDINAL_POSITION
        """)
        columns = cur.fetchall()
        print("\nCurrent transcript_data table structure:")
        for col in columns:
            print(f"Column: {col[0]}, Type: {col[1]}, Max Length: {col[2]}")
            
        # Create transcript_data table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transcript_data (
                transcript_id INT AUTO_INCREMENT PRIMARY KEY,
                application_id VARCHAR(255),
                extracted_name VARCHAR(255),
                extracted_major VARCHAR(255),
                extracted_country VARCHAR(255),
                extracted_degree_level VARCHAR(255),
                extracted_course VARCHAR(255),
                prerequisite_required BOOLEAN DEFAULT FALSE,
                full_text LONGTEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES files(application_id)
            )
        """)
        
        # Alter table to ensure correct column lengths
        cur.execute("""
            ALTER TABLE transcript_data
            MODIFY COLUMN extracted_name VARCHAR(255),
            MODIFY COLUMN extracted_major VARCHAR(255),
            MODIFY COLUMN extracted_country VARCHAR(255),
            MODIFY COLUMN extracted_degree_level VARCHAR(255),
            MODIFY COLUMN extracted_course VARCHAR(255)
        """)
        
        db_conn.commit()
        print("\nTable structure updated successfully")
        
    except Exception as e:
        print(f"\nError checking/updating table structure: {e}")
        raise
    finally:
        cur.close()
        db_conn.close()

# Call this function when the app starts
create_application_data_table()
check_table_structure()

@app.route('/test-read-pdf', methods=['GET'])
def test_read_pdf():
    """Test endpoint to read and process a PDF file"""
    try:
        # Try a different application file
        sample_file = os.path.join(app.config['UPLOAD_FOLDER'], 'Application_1.pdf')
        output_file = "extracted_text.txt"
        
        if not os.path.exists(sample_file):
            return jsonify({"error": "Sample file not found"}), 404
            
        print("\n=== Starting test PDF read ===")
        print(f"Reading file: {sample_file}")
        
        # Process the file using our OCR function
        extracted_text = process_ocr(sample_file)
        
        # Save extracted text to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(extracted_text)
        
        print(f"\nSaved extracted text to {output_file}")
        
        # Extract application data
        application_data = extract_application_data(extracted_text)
        
        return jsonify({
            "message": "File processed successfully",
            "output_file": output_file,
            "extracted_data": application_data
        })
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@app.route('/test-read-image')
def test_read_image():
    try:
        # Try reading one of the screenshot files
        sample_file = os.path.join(app.config['UPLOAD_FOLDER'], 'Screenshot_2025-02-16_154444.png')
        
        if not os.path.exists(sample_file):
            return jsonify({'error': 'Sample file not found'}), 404
            
        # Process the image file
        extracted_text = process_ocr(sample_file)
        print("Extracted text:", extracted_text)
        
        return jsonify({
            'success': True,
            'text': extracted_text
        })
        
    except Exception as e:
        print("Error:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/test-field-extraction', methods=['POST'])
def test_field_extraction():
    """Test endpoint to verify field extraction from application form"""
    try:
        # Get the text from the request
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
            
        print("\n=== Testing Field Extraction ===")
        print("Input text:", text)
        
        # Extract data using our function
        extracted_data = extract_application_data(text)
        
        # Return specifically the fields we're interested in
        result = {
            "program_format": extracted_data["program_format"],
            "field_of_study": extracted_data["field_of_study"],
            "start_semester": extracted_data["start_semester"],
            "start_year": extracted_data["start_year"]
        }
        
        print("Extracted fields:", json.dumps(result, indent=2))
        
        return jsonify({
            "success": True,
            "extracted_fields": result
        })
        
    except Exception as e:
        print(f"Error in test endpoint: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

@app.route('/test-extraction')
def test_extraction():
    """Test endpoint to verify field extraction"""
    test_text = """Which campus do you plan to attend? Main Campus
What do you plan on studying? Computer Science Doctoral
When do you plan to enroll? Fall 2025"""
    
    try:
        # Extract data using our function
        extracted_data = extract_application_data(test_text)
        
        # Return specifically the fields we're interested in
        result = {
            "program_format": extracted_data["program_format"],
            "field_of_study": extracted_data["field_of_study"],
            "start_semester": extracted_data["start_semester"],
            "start_year": extracted_data["start_year"]
        }
        
        print("Extracted fields:", json.dumps(result, indent=2))
        
        return jsonify({
            "success": True,
            "extracted_fields": result,
            "input_text": test_text
        })
        
    except Exception as e:
        print(f"Error in test endpoint: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500

def create_courses_table():
    """Create the courses table if it doesn't exist"""
    print("\n=== Checking courses table ===")
    db_conn = get_db_connection()
    cur = db_conn.cursor()
    try:
        # Create courses table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                course_id INT AUTO_INCREMENT PRIMARY KEY,
                application_id VARCHAR(255) NOT NULL,
                course_name VARCHAR(255) NOT NULL,
                credits DECIMAL(4,2),
                grade VARCHAR(3),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES application_records(application_id)
            )
        """)
        db_conn.commit()
        print("✅ Courses table verified/created successfully")
        
        # Check if any courses exist
        cur.execute("SELECT COUNT(*) FROM courses")
        count = cur.fetchone()[0]
        print(f"Current number of courses in database: {count}")
        
    except Exception as e:
        print(f"❌ Error checking/creating courses table: {str(e)}")
        raise
    finally:
        cur.close()
        db_conn.close()
    print("=== Courses table check complete ===\n")

# Add this line after the other table creation calls
create_courses_table()

def get_courses(application_id):
    """
    Retrieve courses for a specific application ID from the database.
    Returns a list of course dictionaries or empty list if none found.
    """
    print(f"Fetching courses for application ID: {application_id}")
    db_conn = None
    cur = None
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor(dictionary=True)
        
        # Check if application exists
        cur.execute("""
            SELECT application_id 
            FROM application_records 
            WHERE application_id = %s
        """, (application_id,))
        
        if not cur.fetchone():
            print(f"No application found with ID: {application_id}")
            return []
            
        # Get courses with proper null handling
        cur.execute("""
            SELECT 
                course_id,
                COALESCE(course_name, 'Unknown') as course_name,
                COALESCE(credits, 0.0) as credits,
                COALESCE(grade, 'N/A') as grade
            FROM courses 
            WHERE application_id = %s
            ORDER BY course_id
        """, (application_id,))
        
        courses = cur.fetchall()
        print(f"Found {len(courses)} courses for application {application_id}")
        return courses
        
    except Exception as e:
        print(f"Error retrieving courses: {str(e)}")
        return []
        
    finally:
        if cur:
            cur.close()
        if db_conn:
            db_conn.close()
            print("Database connection closed")

@app.route('/get-courses/<application_id>')
def get_courses_route(application_id):
    """Route handler for getting courses by application ID"""
    try:
        courses = get_courses(application_id)
        return jsonify(courses)
    except Exception as e:
        print(f"Error in get_courses route: {str(e)}")
        return jsonify({"error": "Failed to retrieve courses"}), 500

def reprocess_empty_records():
    """Reprocess application forms for records with empty extracted text"""
    print("\n=== Starting to reprocess empty records ===")
    
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    
    try:
        # Get all records with empty extracted text
        cur.execute("""
            SELECT ad.application_id, f.filename
            FROM application_data ad
            JOIN files f ON ad.application_id = f.application_id
            WHERE (ad.extracted_text IS NULL OR ad.extracted_text = '')
              AND f.file_type = 'application'
        """)
        
        records = cur.fetchall()
        print(f"Found {len(records)} records with empty extracted text")
        
        for record in records:
            application_id = record['application_id']
            filename = record['filename']
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            print(f"\nProcessing application_id: {application_id}")
            print(f"File: {file_path}")
            
            if not os.path.exists(file_path):
                print(f"Warning: File not found: {file_path}")
                continue
            
            try:
                # Extract text from the file
                extracted_text = process_ocr(file_path)
                if not extracted_text:
                    print("Warning: No text extracted from file")
                    continue
                
                # Extract application data
                app_data = extract_application_data(extracted_text)
                
                # Update the record
                update_query = """
                    UPDATE application_data
                    SET extracted_text = %s,
                        email = %s,
                        phone = %s,
                        address = %s,
                        city = %s,
                        state = %s,
                        zip_code = %s,
                        country = %s
                    WHERE application_id = %s
                """
                cur.execute(update_query, (
                    extracted_text,
                    app_data['email'],
                    app_data['phone'],
                    app_data['address'],
                    app_data['city'],
                    app_data['state'],
                    app_data['zip_code'],
                    app_data['country'],
                    application_id
                ))
                db_conn.commit()
                print(f"Successfully updated record for {application_id}")
                
            except Exception as e:
                print(f"Error processing {application_id}: {str(e)}")
                traceback.print_exc()
                continue
        
        print("\n=== Reprocessing complete ===")
        
    except Exception as e:
        print(f"Database error: {str(e)}")
        traceback.print_exc()
    finally:
        cur.close()
        db_conn.close()

# Add this route to trigger the reprocessing
@app.route('/reprocess-empty-records', methods=['POST'])
def reprocess_empty_records_route():
    try:
        reprocess_empty_records()
        return jsonify({"message": "Successfully reprocessed empty records"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
