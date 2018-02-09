#!/usr/bin/env python3
from flask import Flask, request, render_template, Response
from flask_restful import Resource, Api
from flask_jsonpify import jsonify
from werkzeug.utils import secure_filename
import subprocess
import os
import requests
import uuid
import datetime
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
try:
    from database import Base, ModelsTable
except (SystemError, ImportError):
    from .database import Base, ModelsTable


# CONFIG

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(CURRENT_FOLDER, 'static', 'models')
TEMP_FOLDER = os.path.join(CURRENT_FOLDER, os.pardir, 'temp')
DB_PATH = os.path.join(CURRENT_FOLDER, 'database', 'database.db')
FBX2GLTF_PATH = os.path.abspath(os.path.join(CURRENT_FOLDER, os.pardir, 'lib', 'fbx2gltf', 'fbx2gltf.py'))
ALLOWED_EXTENSIONS = (['fbx', 'obj', 'zip'])
MAX_UPLOAD_SIZE_MB = 100  # in MB
MAX_UPLOAD_SIZE_B = MAX_UPLOAD_SIZE_MB * 1024 * 1024
DOWNLOAD_URL_BASE = "http://localhost:5022"  # CHANGE TO YOUR OWN SERVER ADDRESS!!

# Database config and initialization
engine = create_engine('sqlite:///' + DB_PATH)
Base.metadata.bind = engine
DBSession = sessionmaker(autocommit=False, bind=engine)
db_session = DBSession()

# Flask and API config
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_SIZE_B * 3  # Set max upload size larger, else broken pipe error thrown
app.config['JSON_SORT_KEYS'] = False  # Prevent sorting of JSON keys

# Set CORS headers
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

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


def make_url(url_type, unique_id, filename):
    """Create a URL to a file on the server.

    Args:
        type (string): `source`, `glb`, or `gltf`.
        unique_id (string): Unique ID of the model we are creating links for.
        filename (string): Filename of the model we are creating links for.

    Returns:
        string: URL to file on server.
    """
    url_base = os.path.join(DOWNLOAD_URL_BASE,
                            'static',
                            os.path.basename(app.config['UPLOAD_FOLDER']),
                            unique_id)
    filename_base = os.path.splitext(filename)[0]

    if url_type == 'source':
        url = os.path.join(url_base, 'source', filename)

    elif url_type == 'glb':
        url = os.path.join(url_base, 'processed', filename_base + '.glb')

    elif url_type == 'gltf':
        url = os.path.join(url_base, 'processed', filename_base + '.gltf')

    elif url_type == 'zip':
        url = os.path.join(url_base, filename_base + '.zip')

    else:
        raise CustomError(400,
                          'bad_request',
                          'You used %s as the type in make_url(). Please use `source`, `glb`, `gltf`, or `zip`.' % url_type)

    return url


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

class Models(Resource):

    def post(self):
        """Upload files.

        Args:
            self

        Returns:
            string: JSON result, or error if one or more of the checks fail.
        """
        # TODO(Nick) Pass parameters to set whether to convert to binary, zip or both, and whether to compress https://github.com/pissang/qtek-model-viewer#converter
        unique_id = uuid.uuid4().hex  # Unique 32 character ID used for event ID and model 
        
        destination_directory = os.path.join(app.config['UPLOAD_FOLDER'], unique_id, 'source')
        processed_directory = os.path.join(app.config['UPLOAD_FOLDER'], unique_id, 'processed')

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
                destination_path = os.path.join(destination_directory, filename)

                # Create destination directory if it does not exist yet
                if not os.path.exists(destination_directory):
                    os.makedirs(destination_directory)

                # Also create the directory for the processed files while we're at it
                if not os.path.exists(processed_directory):
                    os.makedirs(processed_directory)
                
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
                destination_path = os.path.join(destination_directory, filename)

                # Create destination directory if it does not exist yet
                if not os.path.exists(destination_directory):
                    os.makedirs(destination_directory)

                # Also create the directory for the processed files while we're at it
                if not os.path.exists(processed_directory):
                    os.makedirs(processed_directory)

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

        filename_base = os.path.splitext(filename)[0]

        # Convert uploaded file to glTF
        # WARNING: Conversion runs on separate thread, and takes longer to finish than the upload!
        command = [FBX2GLTF_PATH]

        # Default is don't compress
        compressed=False
        if 'compress' in request.form and request.form.get('compress'):
            compress = '-q'
            command.append(compress)
            compressed = True

        # Export as glTF or as GLB
        processed_format = 'gltf'
        if 'binary' in request.form and request.form.get('binary'):
            binary = '-b'
            command.append(binary)
            processed_format = 'glb'

        processed_path = os.path.join(processed_directory, filename_base + '.' + processed_format)
        command.append('-o' + processed_path)
        
        command.append(destination_path)  # Source file path
        
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        #output = process.stdout.read()
        #print(output)
        process.communicate()  # Wait for conversion to finish before continuing

        # Zip glTF and related files from processed directory
        # See: https://stackoverflow.com/a/25650295
        download_format = processed_format
        if processed_format == 'gltf':
            shutil.make_archive(os.path.join(app.config['UPLOAD_FOLDER'], unique_id, filename_base),
                                'zip', 
                                processed_directory)
            download_format = 'zip'


        # Store metadata of upload in database
        new_model = ModelsTable(model_id=unique_id,
                                filename=filename,
                                created_date=datetime.datetime.now(),
                                source_file=make_url('source', unique_id, filename),
                                processed_file=make_url(processed_format, unique_id, filename),
                                downloadable_file=make_url(download_format, unique_id, filename),
                                compressed=compressed)
        db_session.add(new_model)
        db_session.commit()

        # Call Model.get as a function instead of as an API call to save server resources
        result = Model()
        return result.get(unique_id)

    def get(self):
        """List all uploaded files.

        Returns:
            string: JSON array of all files in upload directory.
        """
        # TODO(Nick) Add authentication so that only admins can view list of all uploads
        models = os.listdir(app.config['UPLOAD_FOLDER'])

        return jsonify(models)

    def delete(self):
        """Delete all models older than x hours.

        `hours_old` int should be passed in `data` of delete request.

        Returns:
            string: JSON result, or error if one or more of the checks fail.
        """
        if 'hours_old' in request.form:
            hours_old = int(request.form.get('hours_old'))
        else:
            return make_error(500,
                              'bad_request',
                              'Make sure an `hours_old` int is passed in the `data` of the delete request.'
                              )

        # Find old models in database
        x_hours_ago = datetime.datetime.now() - datetime.timedelta(hours=hours_old)
        models = db_session.query(ModelsTable.model_id).filter(ModelsTable.created_date < x_hours_ago).all()

        # Remove folders and files of old models
        models_folder = app.config['UPLOAD_FOLDER']
        for model_id in models:
            try:
                sub_folder = os.path.join(models_folder, model_id[0])
                shutil.rmtree(sub_folder)
            except OSError:
                print('Folder with name %s could not be deleted, because it could not be found.' % model_id[0])
                pass

        # Remove old models from database
        db_session.query(ModelsTable.model_id).filter(ModelsTable.created_date < x_hours_ago).delete()
        db_session.commit()

        result = {"result": "Successfully deleted all models older than %d hours." % hours_old}
        return jsonify(result)


class Model(Resource):

    def get(self, model_id):
        """Return data about a single model.

        Args:
            model_id (str): The ID of the model you want to view.

        Returns:
            string: JSON result of model metadata.
        """
        # TODO(Nick) Allow parameters to return partial request)
        model = db_session.query(ModelsTable).filter(ModelsTable.model_id == model_id).first()
        if not model:
            return make_error(404,
                              'not_found',
                              'The model you requested with id %s does not exist.' % model_id)

        result = {'model_id': model.model_id,
                  'filename': model.filename,
                  'created_date': model.created_date,
                  'source_file': model.source_file,
                  'processed_file': model.processed_file,
                  'downloadable_file': model.downloadable_file,
                  'compressed': model.compressed}

        return jsonify(result)

    def delete(self, model_id):
        """Delete a single model.

        Args:
            model_id (str): The ID of the model you want to delete.

        Returns:
            string: JSON result, or error if one or more of the checks fail.
        """
        model_folder = os.path.join(app.config['UPLOAD_FOLDER'], model_id)
        try:
            shutil.rmtree(model_folder)
        except OSError:
            return make_error(404,
                              'not_found',
                              'Model with id %s cannot be deleted, because it could not be found.' % model_id
                              )

        # Remove model from database
        model = db_session.query(ModelsTable).filter(ModelsTable.model_id == model_id).first()
        db_session.delete(model)
        db_session.commit()

        result = {"result": "Successfully deleted model with id %s." % model_id}
        return jsonify(result)


class Web(Resource):

    def get(self):
        """ Return the frontend HTML. This can also be run on a completely separate server. """
        return Response(render_template('index.html'), mimetype='text/html')


# ROUTES

api.add_resource(Models, '/v1/models')
api.add_resource(Model, '/v1/models/<model_id>')
api.add_resource(Web, '/')

if __name__ == '__main__':
     app.run(host='0.0.0.0', port='5022')