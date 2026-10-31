import requests

url = "http://127.0.0.1:5000/api/cases"

data = {
    "case_number": "MD-2026-001",
    "case_title": "Drone Flight Investigation",
    "description": "Investigation of a drone flight incident.",
    "opened_at": "2026-10-07 09:30:00",
    "status": "Open",
    "examiner_name": "Lead Examiner"
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.json())