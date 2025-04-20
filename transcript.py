from fpdf import FPDF

class TranscriptPDFRequired(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Sample Transcript - Prerequisite Required", ln=True, align="C")
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

class TranscriptPDFNotNeeded(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "Sample Transcript - Prerequisite Not Needed", ln=True, align="C")
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

# Generate Transcript PDF for Prerequisite Required
pdf_req = TranscriptPDFRequired()
pdf_req.add_page()
pdf_req.set_font("Arial", size=12)
pdf_req.cell(0, 10, "Name: Kelvin Durant", ln=True)
pdf_req.cell(0, 10, "Country: USA", ln=True)
pdf_req.cell(0, 10, "Degree Level: Bachelor's", ln=True)
pdf_req.cell(0, 10, "Program: History", ln=True)
pdf_req.ln(10)
pdf_req.set_font("Arial", "B", 14)
pdf_req.cell(0, 10, "Courses and Grades:", ln=True)
pdf_req.ln(5)
pdf_req.set_font("Arial", size=12)
courses_req = [
    ("World History", "A"),
    ("Political Science", "B"),
    ("Philosophy", "A-"),
    ("Mathematics", "B+")
]
for course, grade in courses_req:
    pdf_req.cell(0, 10, f"{course}: {grade}", ln=True)
pdf_req_file = "Kelvin_Durant_Prerequisite_Required.pdf"
pdf_req.output(pdf_req_file)
print(f"Generated {pdf_req_file}")

# Generate Transcript PDF for Prerequisite Not Needed
pdf_not = TranscriptPDFNotNeeded()
pdf_not.add_page()
pdf_not.set_font("Arial", size=12)
pdf_not.cell(0, 10, "Name: Kelvin Durant", ln=True)
pdf_not.cell(0, 10, "Country: USA", ln=True)
pdf_not.cell(0, 10, "Degree Level: Master's", ln=True)
pdf_not.cell(0, 10, "Program: Computer Science", ln=True)
pdf_not.ln(10)
pdf_not.set_font("Arial", "B", 14)
pdf_not.cell(0, 10, "Courses and Grades:", ln=True)
pdf_not.ln(5)
pdf_not.set_font("Arial", size=12)
courses_not = [
    ("Advanced Programming Techniques", "A"),
    ("Software Engineering", "A-"),
    ("Data Structures and Programming", "B+"),
    ("Algorithms", "A")
]
for course, grade in courses_not:
    pdf_not.cell(0, 10, f"{course}: {grade}", ln=True)
pdf_not_file = "Kelvin_Durant_Prerequisite_Not_Needed.pdf"
pdf_not.output(pdf_not_file)
print(f"Generated {pdf_not_file}")
