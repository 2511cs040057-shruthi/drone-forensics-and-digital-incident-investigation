import requests

url = "http://127.0.0.1:5000/api/cases"

data = {
    "case_number": "MD-2026-DELETE",
    "case_title": "Delete Test Case",
    "description": "Temporary case for testing delete API.",
    "opened_at": "2026-10-07 10:00:00",
    "status": "Open",
    "examiner_name": "Test Examiner"
}

response = requests.post(url, json=data)

print("Create Status:", response.status_code)
print("Create Response:", response.json())

case_id = response.json()["case_id"]

delete_url = f"{url}/{case_id}"

response = requests.delete(delete_url)

print("Delete Status:", response.status_code)
print("Delete Response:", response.json())