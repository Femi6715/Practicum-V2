import mysql.connector
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pytesseract
import cv2
import os
from werkzeug.utils import secure_filename
import re

app = Flask(__name__)
CORS(app)

# Configure MySQL Database Connection (global connection for some routes)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="62221085",       # Replace with your actual MySQL password
    database="mis_gapms"       # Replace with your actual database name
)
cursor = db.cursor()

# Helper function to get a fresh connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="62221085",
        database="mis_gapms"
    )

# Set Upload Folder
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Set Tesseract OCR Path (For Windows Users)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Basic OCR Processing Function: returns extracted text
def process_ocr(file_path):
    image = cv2.imread(file_path)
    if image is None:
        return "", False
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    custom_config = r'--oem 3 --psm 6'
    extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
    # For now, we don't use the boolean flag here because we will recalc after field extraction
    return extracted_text, False

# Function to extract fields from transcript text using regex
def extract_transcript_data(text):
    # Dummy extraction using regex; adjust these patterns based on your transcript format
    name_match = re.search(r'Name:\s*(.*)', text)
    country_match = re.search(r'Country:\s*(.*)', text)
    degree_match = re.search(r'Degree Level:\s*(.*)', text)
    course_match = re.search(r'Course:\s*(.*)', text)
    
    extracted_name = name_match.group(1).strip() if name_match else "Unknown"
    extracted_country = country_match.group(1).strip() if country_match else "Unknown"
    extracted_degree_level = degree_match.group(1).strip() if degree_match else "Unknown"
    extracted_course = course_match.group(1).strip() if course_match else "Unknown"
    
    # Example logic: if degree level is "Bachelor" or the course doesn't contain "Programming", prerequisites are required.
    prerequisite_required = True if extracted_degree_level.lower() == "bachelor" or "programming" not in extracted_course.lower() else False
    
    return extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required

# Function to store transcript data into the transcript_data table
def store_transcript_data(application_id, extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, details):
    query = """
        INSERT INTO transcript_data (application_id, extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (application_id, extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, details))
    db.commit()

# Upload and Process File Route (for transcripts)
# @app.route('/upload', methods=['GET', 'POST'])
# def upload_files():
#     if request.method == 'POST':
#         if 'file' not in request.files:
#             return jsonify({"error": "No file part"}), 400

#         file = request.files['file']
#         if file.filename == '':
#             return jsonify({"error": "No selected file"}), 400

#         if file and allowed_file(file.filename):
#             filename = secure_filename(file.filename)
#             file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#             file.save(file_path)

#             # Perform OCR processing to extract full text
#             extracted_text, _ = process_ocr(file_path)
#             # Extract specific fields from the OCR text
#             extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required = extract_transcript_data(extracted_text)

#             # For demonstration, assume the application_id is passed via form data (default 1 for testing)
#             application_id = request.form.get("application_id", 1)
#             store_transcript_data(application_id, extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, extracted_text)

#             return jsonify({
#                 "extracted_text": extracted_text,
#                 "extracted_name": extracted_name,
#                 "extracted_country": extracted_country,
#                 "extracted_degree_level": extracted_degree_level,
#                 "extracted_course": extracted_course,
#                 "prerequisite": prerequisite_required
#             })

#     return render_template('upload.html')
@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            try:
                extracted_text, _ = process_ocr(file_path)
                prerequisite_required = any(keyword.lower() in extracted_text.lower() for keyword in ["programming"])
            except Exception as e:
                return jsonify({"error": str(e)}), 500
            return jsonify({
                "text": extracted_text,
                "prerequisite": prerequisite_required
            })
    return render_template('upload.html')

# Other Routes remain unchanged
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/review')
def review_applications():
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

# New Route: Get All Students from Users Table
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

# Get Transcript data 
@app.route('/get-transcript-data')
def get_transcript_data():
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    query = "SELECT transcript_id, extracted_name, extracted_country, extracted_degree_level, extracted_course, prerequisite_required, details FROM transcript_data"
    cur.execute(query)
    transcripts = cur.fetchall()
    cur.close()
    db_conn.close()
    return jsonify(transcripts)

# @app.route('/review', methods=['GET'])
# def review_applications():
#     # If the request is an AJAX request, return JSON data from transcript_data table
#     if request.headers.get("X-Requested-With") == "XMLHttpRequest":
#         db_conn = get_db_connection()
#         cur = db_conn.cursor(dictionary=True)
#         query = """
#             SELECT transcript_id, extracted_name, extracted_country, extracted_degree_level,
#                    extracted_course, prerequisite_required, details
#             FROM transcript_data
#         """
#         cur.execute(query)
#         transcripts = cur.fetchall()
#         cur.close()
#         db_conn.close()
#         return jsonify(transcripts)
#     # Otherwise, render the review template
#     return render_template('review.html')
def process_ocr(file_path):
    image = cv2.imread(file_path)
    if image is None:
        raise ValueError("Could not read the image. Ensure the file is a valid image format.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    custom_config = r'--oem 3 --psm 6'
    extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
    prerequisite_keywords = ["Introduction to Programming", "Computer Science Basics", "BUIS 360", "BUIS 305"]
    prerequisite_required = any(keyword.lower() in extracted_text.lower() for keyword in prerequisite_keywords)
    return extracted_text, prerequisite_required



if __name__ == "__main__":
    app.run(port=5000, debug=True)
