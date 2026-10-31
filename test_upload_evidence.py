import requests

url = "http://127.0.0.1:5000/api/evidence/upload"

files = {
    "file": open("sample_flight_log.txt", "rb")
}

data = {
    "case_id": "1",
    "file_type": "Flight Log"
}

response = requests.post(url, files=files, data=data)

files["file"].close()

print("Status Code:", response.status_code)
print("Response:", response.json())