# Builds a jessie linux distribution with Python 3.3 and then installs the glTF API
# docker build --tag headjack/gltf:0.0.1 .


FROM headjack/python:3.3.7-jessie-fbx

# Copy all project files
COPY . /var/www

# Install all Python packages in requirements.txt
RUN pip install -r /var/www/requirements.txt

# Start API
CMD ["python", "/var/www/app/api.py"]