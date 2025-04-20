from app import extract_application_data

# Sample application form text
sample_text = """
APPLICATION FORM

Full Name: John Doe
Date of Birth: 01/01/1990
Gender: Male
Email Address: john.doe@example.com
Phone: 123-456-7890
Address: 123 Main St
City: Anytown
State: CA
Zip Code: 12345
Country: USA

Do you reside in the United States? [X] Yes [ ] No

What is your country of citizenship? USA

What is your visa type? N/A

Which campus do you plan to attend? Main Campus

What do you plan on studying? Information Systems

When do you plan to enroll? Fall 2023
"""

# Extract application data
app_data = extract_application_data(sample_text)

# Print the extracted data
print("Extracted Application Data:")
print(f"Name: {app_data['name']}")
print(f"Email: {app_data['email']}")
print(f"Phone: {app_data['phone']}")
print(f"Field of Study: {app_data['field_of_study']}")
print(f"Program Format: {app_data['program_format']}")
print(f"Start Semester: {app_data['start_semester']}")
print(f"Start Year: {app_data['start_year']}") 