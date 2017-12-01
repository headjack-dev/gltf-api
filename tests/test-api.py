# Run test API
import requests


# Upload an unsupported file
print("Upload started")
url = 'http://127.0.0.1:5010/v1/models'  # API endpoint
filename = 'test.png'
file = open(filename, 'rb')  # File to upload
r = requests.post(url=url, data={'uploaded_file': filename}, files={'file': file})
print(r.status_code)
print(r.text)


# Upload a supported file
print("Upload started")
url = 'http://127.0.0.1:5010/v1/models'  # API endpoint
filename = 'test.fbx'
file = open(filename, 'rb')  # File to upload
r = requests.post(url=url, data={'uploaded_file': filename}, files={'file': file})
print(r.status_code)
print(r.text)


# Retrieve list of uploaded files
print("List of files")
url = 'http://127.0.0.1:5010/v1/models'  # API endpoint
# r = requests.get('https://api.github.com/user', auth=('user', 'pass')), because we need authentication for this one
r = requests.get(url=url)
print(r.status_code)
print(r.text)