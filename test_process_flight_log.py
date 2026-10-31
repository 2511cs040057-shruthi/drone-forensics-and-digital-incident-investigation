import requests

url = "http://127.0.0.1:5000/api/flight-log/process"

files = {
    "file": open("sample_flight_log.txt", "rb")
}

response = requests.post(url, files=files)

files["file"].close()

print("Status Code:", response.status_code)
print("Response:", response.json())