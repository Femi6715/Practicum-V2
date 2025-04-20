import re

# Test text with different email formats
test_text = """
Name: John Doe
Email Address: john.doe@example.com
Phone: 123-456-7890
"""

# Email patterns
email_patterns = [
    r"Email (?:Address)?[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"E-mail[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"Email Address[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
    r"Email\s+Address[:]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
]

# Test each pattern
for i, pattern in enumerate(email_patterns):
    match = re.search(pattern, test_text, re.IGNORECASE)
    if match:
        print(f"Pattern {i+1} matched: {match.group(1)}")
    else:
        print(f"Pattern {i+1} did not match") 