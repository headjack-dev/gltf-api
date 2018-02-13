# glTF converter API
Brought to you by [Headjack](https://headjack.io)

API to convert OBJ, FBX and COLLADA files to [glTF](https://github.com/KhronosGroup/glTF) or GLB, based on the [ClayGL converter](https://github.com/pissang/clay-viewer#converter). 

## Usage

To convert a 3D model to glTF, go to [the glTF API website](https://github.com/pissang/clay-viewer#converter) and upload your 3D model as OBJ, FBX or COLLADA. Zipped files are also accepted.

*Make sure your models use **relative** texture paths, else the model viewer on the page will not be able to preview your converted model.*

If you want to use the API directly instead of the web interface, use a POST request to the `/models` endpoint. You can POST either a binary file.

```
import requests
url = 'https://gltfapi.co/v1/models'
file = open('test.fbx', 'rb')
requests.post(url=url, files={'file': file})
```

Or you can POST an url to a hosted file.

```
import requests
url = 'https://gltfapi.co/v1/models'
source_path = 'https://example.com/test.fbx'
requests.post(url=url, data={'source_path': source_path})
```

After uploading, you can use the `/models/{id}` endpoint to GET information about a single model.

```
import requests
url = 'https://gltfapi.co/v1/models/1234567890'
requests.get(url=url)
```

The response contains the following information:

* `model_id` The unique ID of the model
* `filename` Original filename of the model
* `created_at` The upload timestamp
* `source_file` Url to original upload
* `processed_file` Url to the converted model (glTF or GLB)
* `downloadable_file` Url to a download of the converted model (ZIP or GLB)
* `compressed` Boolean indicating whether compression was applied

### Limits

To protect the server, the API rate limit is currently set to 200 a day, 50 per hour.


## Getting Started

These instructions will tell you how to get a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Download and install [Docker](https://www.docker.com/community-edition).

### Installing

Use command line to change to the project root directory, which contains the `Dockerfile`.

```
cd /path/to/project
```

Next, build the Docker image, using `--tag` to give it a name.

```
docker build --tag headjack/gltf:0.0.1 .
```

Now run the Docker container to start the API.

```
docker run -p 5022:5022 --name gltf --mount source=modelsvol,target=/var/www/static/models --mount source=modelsdb,target=/var/www/app/database.db headjack/gltf:0.0.1
```

As you can see, the run command contains several parameters:

* `-p` maps port 5022 inside your Docker container to localhost port 5022. Change this if you want to use a different port to access the glTF API.
* `--name` gives the Docker container an easy to reference name. Change to whatever you like.
* `--mount` is used to create persistent storage for the uploaded models, as well as the database, so that they are not discarded when the container is restarted.

Now that the container is running, you can go to `localhost:5022` and you should see the upload page for the glTF converter.

The following endpoints exist:

* `/:GET` HTML5 upload form for the glTF converter
* `/v1/models:GET` Retrieves a list of uploaded models (protected)
* `/v1/models:POST` Post an FBX, ZIP or OBJ file to the converter
* `/v1/models:DELETE` Delete all models older than `hours_old` parameter (protected)
* `/v1/models/{id}:GET` Retrieve information about a single model
* `/v1/models/{id}:DELETE` Delete a single model (protected)

The `protected` endpoints require you to pass a `key` parameter in the request, of which the value can be set using the `API_KEY` variable in `api.py`.

## Tests

In the folder `/tests` you find the file `test-api.py`, which performs several requests to see if the API is working correctly. You will have to first change the filenames and urls used in the file to ones that you would like to use in your tests, then simply run the script.

```
python test-api.py
```

## Deployment

The glTF API runs on an Amazon EC2 instance. I'll briefly explain the deployment process, using OSX as the development platform.

First, [install the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/installing.html).

```
brew install awscli
```

Check if the install succeeded by typing `aws --version`.

Next, sign in to the AWS console and create a new user with EC2 permissions, and write down the `access key` and and `secret key` in a secure location. Then configure the AWS CLI with these credentials.

```
aws configure
```

*It is also possible to manually create the AWS credential files, in which case the AWS CLI is not required.*

You can now start a ["Dockerized" EC2 instance](https://docs.docker.com/machine/examples/aws/) using the `docker-machine` command.

```
docker-machine create --driver amazonec2 --amazonec2-open-port 5022 --amazonec2-region us-east-1 gltf-api
```

You might have to run an `eval` command to make the instance active.

```
docker-machine env gltf-api
eval $(docker-machine env gltf-api)
```

You can also choose to use the AWS CLI to start an EC2 instance and then install Docker manually, but we will not cover this here.

Now copy all glTF API project files to the EC2 instance.

```
docker-machine scp -r -d /path/to/gltf-api/ gltf-api:/home/ubuntu/
```

Once all files are copied, connect with ssh to your EC2 instance.

```
docker-machine ssh gltf-api
```

Change to your project folder.

```
cd /home/ubuntu/project-folder
```

Next, build the Docker image, using `--tag` to give it a name.

```
sudo docker build --tag headjack/gltf:0.0.1 .
```

Now run the Docker container to start the API.

```
sudo docker run -p 5022:80 --name gltf --mount source=modelsvol,target=/var/www/static/models --mount source=modelsdb,target=/var/www/app/database.db headjack/gltf:0.0.1
```

Congratulations, you have just successfully deployed your API to EC2!

If you want to access the API through a domain instead of an IP address, you can use [Amazon Route53](https://aws.amazon.com/route53) to link your domain to your instance.

To create persistent storage, you would need to integrate [Amazon EBS](https://aws.amazon.com/ebs/) as well, but that is outside the scope of this document.

## Built With

* [ClayGL converter](https://github.com/pissang/clay-viewer#converter) - Python glTF converter
* [Autodesk FBX SDK](http://usa.autodesk.com/adsk/servlet/pc/item?siteID=123112&id=10775847) - SDK to handle FBX files
* [three.js](https://threejs.org/docs/#examples/loaders/GLTFLoader) - Used for the model preview window

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details