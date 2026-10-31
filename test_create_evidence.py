import requests

url = "http://127.0.0.1:5000/api/evidence"

data = {
    "case_id": 1,
    "file_name": "flight_log.bin",
    "file_type": "Flight Log",
    "file_size": 2048,
    "file_path": "evidence/flight_log.bin",
    "sha256_hash": "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.json())