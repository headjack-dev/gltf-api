#!/usr/bin/env python3
from flask import Flask, request, redirect
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from flask_jsonpify import jsonify
from werkzeug.utils import secure_filename
import subprocess
import os
import requests
import uuid

# Follow: https://google.github.io/styleguide/pyguide.html
__author__ = "Nick Kraakman - nick@headjack.io"


# CONFIG

UPLOAD_FOLDER = '../static/models'
TEMP_FOLDER = '../temp'
ALLOWED_EXTENSIONS = (['fbx', 'obj', 'zip', 'glb'])
MAX_UPLOAD_SIZE_MB = 100  # in MB
MAX_UPLOAD_SIZE_B = MAX_UPLOAD_SIZE_MB * 1024 * 1024

db = create_engine('sqlite:///database.db')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_B * 3  # Set max upload size larger, else broken pipe error thrown
api = Api(app)


# FUNCTIONS

def allowed_file(filename):
    """Check if uploaded file extension is allowed.

    Args:
        filename (str): Filename to check.

    Returns:
        bool: True if file extension is allowed, False otherwise.
        string: Extension of the checked file.
    """
    extension = filename.rsplit('.', 1)[1].lower()
    result = '.' in filename and \
        extension in ALLOWED_EXTENSIONS
    return result, extension


def download_file(source_path, destination_path):
    """Download a file from a url to a destination.

    Args:
        source_path (str): Url to file that needs to be downloaded.
        destination_path (str): Path where to download the file to.

    Returns:
        bool: True if download succeeded, False otherwise.
    """
    r = requests.get(source_path, timeout=30, stream=True)  # Stream to prevent file to be stored in memory
    size = 0

    # If Content-Length is set
    if r.headers.get('Content-Length') and int(r.headers.get('Content-Length')) > MAX_UPLOAD_SIZE_B:
        r.close()
        raise CustomError(413,
                          'payload_too_large',
                          'The file you tried to upload is larger than the %dMB limit. Please upload '
                          'a smaller file.' % MAX_UPLOAD_SIZE_MB)

    destination_directory = os.path.dirname(destination_path)

    # Create destination directory if it does not exist yet
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)

    # If Content-Length is not set
    if r.status_code == 200:
        with open(destination_path+'_temp', 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # Filter out keep-alive new chunks
                    size += len(chunk)
                    if size > MAX_UPLOAD_SIZE_B:
                        r.close()
                        f.close()
                        os.remove(destination_path+'_temp')  # Remove unfinished download
                        os.rmdir(destination_directory)  # Remove now empty folder
                        raise CustomError(413,
                                          'payload_too_large',
                                          'The file you tried to upload is larger than the %dMB limit. Please upload '
                                          'a smaller file.' % MAX_UPLOAD_SIZE_MB)
                    else:
                        f.write(chunk)
    else:
        raise CustomError(404,
                          'file_not_found',
                          'The file at %s could not be found. Please check your source_path.' % source_path)
    os.rename(destination_path+'_temp', destination_path)  # Rename _temp file to indicate download completed
    r.close()


def get_size(file_object):
    """Get the file size of a file uploaded through a form.

    Args:
        file_object (object): A file from the `files` part of a POST request.


    Returns:
        int: File size in bytes.
    """
    if file_object.content_length:
        return file_object.content_length

    try:
        pos = file_object.tell()
        file_object.seek(0, 2)  # Seek to end
        size = file_object.tell()
        file_object.seek(pos)  # Back to original position
        return size
    except (AttributeError, IOError):
        pass

    # in-memory file object that doesn't support seeking or tell
    return 0  # Assume small enough


def make_error(status_code, error_code, message='', help_url=''):
    """Create an error message.

    Use as follows:
    error = make_error(413, 'file_too_big', 'The file you tried to upload is 210MB, but 200MB is the limit')
    return error

    Args:
        status_code (int): HTTP status code, e.g. `404`.
        error_code (str): Internal error code of the API, e.g. `OAuthException`.
        message (str): A human readable, verbose error message saying what is wrong, with what, and how to fix it.
        help_url (str): Direct URL to more information about this particular error.

    Returns:
        object: Object with the entire JSON response to return to the client.
    """
    response = jsonify({
        'error': {
            'type': error_code,
            'message': message,
            'help_url': help_url
        }
    })
    response.status_code = status_code
    return response


# CUSTOM EXCEPTIONS

class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class CustomError(Error):
    """Custom exception, raised when an uploaded file is too large or when URL does not return 200 status.

    Attributes:
        status_code (int): HTTP status code, e.g. `404`.
        error_code (str): Internal error code of the API, e.g. `OAuthException`.
        message (str): A human readable, verbose error message saying what is wrong, with what, and how to fix it.
        help_url (str): Direct URL to more information about this particular error.
    """
    def __init__(self, status_code, error_code, message='', help_url=''):
        self.status_code = status_code
        self.type = error_code
        self.message = message
        self.help_url = help_url


# API ENDPOINTS

class Employees(Resource):

    def get(self):
        conn = db_connect.connect()  # connect to database
        query = conn.execute("select * from employees")  # This line performs query and returns json result
        return {'employees': [i[0] for i in query.cursor.fetchall()]}  # Fetches first column that is Employee ID


class Tracks(Resource):

    def get(self):
        conn = db_connect.connect()
        query = conn.execute("select trackid, name, composer, unitprice from tracks;")
        result = {'data': [dict(zip(tuple(query.keys()), i)) for i in query.cursor]}
        return jsonify(result)


class EmployeesName(Resource):

    def get(self, employee_id):
        conn = db_connect.connect()
        query = conn.execute("select * from employees where EmployeeId =%d " % int(employee_id))
        result = {'data': [dict(zip(tuple(query.keys()), i)) for i in query.cursor]}
        return jsonify(result)


class Models(Resource):

    def post(self):
        """Upload files.

        Args:
            self

        Returns:
            string: JSON result, or error if one or more of the checks fail.
        """
        # TODO(Nick) Write server errors to log file
        # TODO(Nick) Store metadata of upload in database
        # TODO(Nick) Pass parameters to set whether to convert to binary, zip or both, and whether to compress https://github.com/pissang/qtek-model-viewer#converter
        unique_id = uuid.uuid4().hex  # Unique 32 character ID used for event ID and model ID

        # Store request as an event in the database
        # TODO(Nick) Store every request in the events database table

        # TODO(Nick): Refactor the IF statement below to remove duplicate code
        if 'file' in request.files:
            # File data uploaded
            file = request.files['file']
            filename = secure_filename(file.filename)
            allowed, extension = allowed_file(filename)

            if get_size(file) > MAX_UPLOAD_SIZE_B:
                return make_error(413,
                                  'payload_too_large',
                                  'The file you tried to upload is larger than the %dMB limit. Please upload '
                                  'a smaller file.' % MAX_UPLOAD_SIZE_MB)

            # Save uploaded file
            if allowed:
                destination_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_id, filename)
                destination_directory = os.path.dirname(destination_path)

                # Create destination directory if it does not exist yet
                if not os.path.exists(destination_directory):
                    os.makedirs(destination_directory)

                file.save(destination_path)

            else:
                return make_error(415,
                                  'unsupported_file',
                                  'The %s extension is not allowed, please upload an fbx, obj, or zip file' % extension)

        elif 'source_path' in request.form:
            # URL sent, no file data uploaded
            source_path = request.form.get('source_path')
            filename = secure_filename(source_path.split('/')[-1])
            allowed, extension = allowed_file(filename)

            # Download file
            if allowed:
                destination_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_id, filename)
                try:
                    download_file(source_path, destination_path)
                except CustomError as e:
                    return make_error(e.status_code, e.type, e.message, e.help_url)

            else:
                return make_error(415,
                                  'unsupported_file',
                                  'The %s extension is not allowed, please upload an fbx, obj, or zip file' % extension)

        else:
            return make_error(400,
                              'bad_request',
                              'Neither file nor source_path present in the request')

        if not allowed:
            return make_error(415,
                              'unsupported_file',
                              'The %s extension is not allowed, please upload an fbx, obj, or zip file' % extension)

        # Convert uploaded file to glTF
        # WARNING: Conversion runs on separate thread, and takes longer to finish than the upload!
        command = ['../lib/fbx2gltf.py']

        # Default is don't compress
        if 'compress' in request.form and request.form.get('compress'):
            compress = '-q'
            command.append(compress)

        # TODO(Nick) Add binary export option once it becomes available in the fbx2gltf library
        # if 'binary' in request.form and request.form.get('binary'):
        #    binary = '-b'
        #    command.append(binary)

        command.append(destination_path)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        process.communicate()  # Wait for conversion to finish before continuing

        return redirect('http://127.0.0.1:5018/v1/models/' + unique_id)

    def get(self):
        """List all uploaded files.

        Args:
            self

        Returns:
            string: JSON array of all files in upload directory.
        """
        # TODO(Nick) Add authentication so that only admins can view list of all uploads
        result = os.listdir(app.config['UPLOAD_FOLDER'])
        return jsonify(result)


class Model(Resource):

    def get(self, model_id):
        """Return data about a single model.

        Args:
            self
            model_id (str): The ID of the model you want to view.

        Returns:
            string: JSON result of model metadata.
        """
        # TODO(Nick) Allow parameters to return model in specific format (Original, glb (binary), or glTF (zip))
        result = {'result': 'Model id = ' + model_id}
        return jsonify(result)

    def delete(self, model_id):
        """Delete a single model.

        Args:
            self
            model_id (str): The ID of the model you want to delete.

        Returns:
            string: JSON result, or error if one or more of the checks fail.
        """
        # TODO(Nick) Delete models automatically after 1 week


# ROUTES

api.add_resource(Employees, '/v1/employees')
api.add_resource(Tracks, '/v1/tracks')
api.add_resource(EmployeesName, '/v1/employees/<employee_id>')
api.add_resource(Models, '/v1/models')
api.add_resource(Model, '/v1/models/<model_id>')

if __name__ == '__main__':
     app.run(port='5018')