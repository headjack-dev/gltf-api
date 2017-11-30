# Run test API
import requests

# Upload a file
print("Upload started")
url = 'http://127.0.0.1:5010/upload' # API endpoint
filename = 'test.png'
file = open(filename, 'rb') # File to upload
r = requests.post(url=url, data={'title': filename}, files={'file': file})
print(r.status_code)
print(r.text)