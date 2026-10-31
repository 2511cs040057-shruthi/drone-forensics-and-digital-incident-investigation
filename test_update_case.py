import requests

url = "http://127.0.0.1:5000/api/cases/1"

data = {
    "case_number": "MD-2026-001",
    "case_title": "Updated Drone Investigation",
    "description": "Case details updated during investigation.",
    "opened_at": "2026-10-07 09:30:00",
    "status": "In Progress",
    "examiner_name": "Lead Examiner"
}

response = requests.put(url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.json())