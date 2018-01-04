# Builds a jessie linux distribution with Python 3.3 and then installs the glTF API
# docker build --tag headjack/gltf:0.0.1 .


FROM headjack/python:3.3.7-jessie-fbx
MAINTAINER Nick Kraakman

# copy all project files
COPY . /var/www

# install all Python packages in requirements.txt and create database
RUN pip install -r /var/www/requirements.txt \
	&& cd /var/www/app \
	&& python database.py

# start API
CMD ["python", "/var/www/app/api.py"]