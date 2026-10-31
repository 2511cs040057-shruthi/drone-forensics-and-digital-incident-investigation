import requests

url = "http://127.0.0.1:5000/api/test"

response = requests.get(url)

print("Status Code:", response.status_code)
print("Response:", response.json())