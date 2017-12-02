#!/usr/bin/env python3
# https://google.github.io/styleguide/pyguide.html
__author__ = "Nick Kraakman - nick@headjack.io"

from flask import Flask, request  # redirect, url_for
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from flask_jsonpify import jsonify
from werkzeug.utils import secure_filename
import subprocess, os, requests, sys


# CONFIG

UPLOAD_FOLDER = '../static/uploads'
ALLOWED_EXTENSIONS = (['fbx', 'obj', 'zip', 'glb'])
MAX_UPLOAD_SIZE_MB = 200  # in MB
MAX_UPLOAD_SIZE_B = MAX_UPLOAD_SIZE_MB * 1024 * 1024

db_connect = create_engine('sqlite:///chinook.db')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_B  # Set max upload size
# Define custom error messages
errors = {
    'RequestEntityTooLarge': {
        'message': 'Source file too large. Please upload a file smaller than %sMB' % MAX_UPLOAD_SIZE_MB,
        'status': 413,
    }
}
api = Api(app, errors=errors)


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
    r = requests.get(source_path, timeout=10, stream=True)  # Stream to prevent file to be stored in memory
    content = b''

    if r.status_code == 200:
        with open(destination_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    content += chunk
                    if len(content) > MAX_UPLOAD_SIZE_B:
                        r.close()
                        raise ValueError('Source file too large. Please upload a file smaller than %sMB' % MAX_UPLOAD_SIZE_MB)
                    f.write(chunk)
        success = True
    else:
        success = False

    r.close()
    return success


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
        # TODO(Nick): Refactor the IF statement below to remove duplicate code
        destination_path = ''

        if 'file' in request.files:
            # File data uploaded
            file = request.files['file']
            filename = secure_filename(file.filename)
            allowed, extension = allowed_file(filename)

            # Save uploaded file
            if allowed:
                destination_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(destination_path)
            else:
                print('The %s extension is not allowed, please upload an fbx, obj, or zip file' % extension)

        elif 'source_path' in request.form:
            # URL sent, no file data uploaded
            source_path = request.form.get('source_path')
            filename = secure_filename(source_path.split('/')[-1])
            allowed, extension = allowed_file(filename)

            # Download file
            if allowed:
                destination_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                download_file(source_path, destination_path)
            else:
                print('The %s extension is not allowed, please upload an fbx, obj, or zip file' % extension)

        else:
            error = {'error': 'Neither file nor source_path present in the request'}
            return jsonify(error)

        if not allowed:
            error = {'error': 'The %s extension is not allowed, please upload an fbx, obj, or zip file' % extension}
            return jsonify(error)

        # Convert uploaded file to glTF
        # WARNING: Conversion runs on separate thread, and takes longer to finish than the upload!
        command = [
            '../lib/fbx2gltf.py',
            destination_path
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        process.communicate()  # Wait for subprocess to finish
        # Write stdout to logfiles
        # sys.stdout = open(cwd+'/vrencoder_log.txt', 'w', 1)
        # sys.stderr = open(cwd+'/vrencoder_errors.txt', 'w', 1)

        # TODO(Nick) Return correct status code if uploaded file is too large
        # TODO(Nick) Store metadata of upload in database
        # TODO(Nick) Pass parameters to set whether to convert to binary, zip or both, and whether to compress https://github.com/pissang/qtek-model-viewer#converter
        # TODO(Nick) Upload/save/convert initially to temp folder, and then copy to static/models after completed
        result = {'result': 'Successfully saved %s to %s' % (filename, destination_path)}
        return jsonify(result)
        # return redirect(url_for('uploaded_file', filename=filename)) # In case we want to display a webpage

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

    def delete(self, model_id):
        """Delete a single model.

        Args:
            self
            model_id (str): The ID of the model you want to delete.

        Returns:
            string: JSON result, or error if one or more of the checks fail.
        """


# ROUTES

api.add_resource(Employees, '/v1/employees')
api.add_resource(Tracks, '/v1/tracks')
api.add_resource(EmployeesName, '/v1/employees/<employee_id>')
api.add_resource(Models, '/v1/models')
api.add_resource(Model, '/v1/models/<model_id>')

if __name__ == '__main__':
     app.run(port='5011')