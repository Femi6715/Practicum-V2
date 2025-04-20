import requests
import json

test_text = """Which campus do you plan to attend? Main Campus
What do you plan on studying? Computer Science Doctoral
When do you plan to enroll? Fall 2025"""

response = requests.post(
    'http://localhost:5000/test-field-extraction',
    json={'text': test_text}
)

print("Status Code:", response.status_code)
print("Response:", json.dumps(response.json(), indent=2)) 