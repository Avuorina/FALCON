import requests

response = requests.post(
    "http://127.0.0.1:8000/chat",
    json={"message": "こんにちは"},
)

print(response.status_code)
print(response.json())