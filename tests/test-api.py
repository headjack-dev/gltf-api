# Run test API
import requests


# Upload an unsupported file
print("Upload unsupported file")
url = 'http://127.0.0.1:5011/v1/models'  # API endpoint
filename = 'test.png'
file = open(filename, 'rb')  # File to upload
r = requests.post(url=url, data={'uploaded_file': filename}, files={'file': file})
print(r.status_code)
print(r.text)

# Upload a supported file
print("Upload supported file")
url = 'http://127.0.0.1:5011/v1/models'  # API endpoint
filename = 'test.fbx'
file = open(filename, 'rb')  # File to upload
r = requests.post(url=url, data={'uploaded_file': filename}, files={'file': file})
print(r.status_code)
print(r.text)


# Upload a supported file by sending the url
print("Post source_path to supported file")
url = 'http://127.0.0.1:5011/v1/models'  # API endpoint
source_path = 'https://purplepill.io/wp-includes/3d/test.FBX'
r = requests.post(url=url, data={'source_path': source_path})
print(r.status_code)
print(r.text)


# Retrieve list of uploaded files
print("Retrieve list of models")
url = 'http://127.0.0.1:5011/v1/models'  # API endpoint
# r = requests.get('https://api.github.com/user', auth=('user', 'pass')), because we need authentication for this one
r = requests.get(url=url)
print(r.status_code)
print(r.text)