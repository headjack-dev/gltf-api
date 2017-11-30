from flask import Flask, request, redirect, url_for
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from flask.ext.jsonpify import jsonify
from werkzeug.utils import secure_filename
import os

# Config
db_connect = create_engine('sqlite:///chinook.db')
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '../static/uploads' # Upload folder
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
api = Api(app)

# Check if uploaded file extension is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Define API endpoints
class Employees(Resource):
    def get(self):
        conn = db_connect.connect() # connect to database
        query = conn.execute("select * from employees") # This line performs query and returns json result
        return {'employees': [i[0] for i in query.cursor.fetchall()]} # Fetches first column that is Employee ID

class Tracks(Resource):
    def get(self):
        conn = db_connect.connect()
        query = conn.execute("select trackid, name, composer, unitprice from tracks;")
        result = {'data': [dict(zip(tuple (query.keys()) ,i)) for i in query.cursor]}
        return jsonify(result)

class Employees_Name(Resource):
    def get(self, employee_id):
        conn = db_connect.connect()
        query = conn.execute("select * from employees where EmployeeId =%d "  %int(employee_id))
        result = {'data': [dict(zip(tuple (query.keys()) ,i)) for i in query.cursor]}
        return jsonify(result)

class UploadFile(Resource):
    #def post(self, fname):
    def post(self):
        file = request.files['file']
        print(file)
        if file and allowed_file(file.filename):
            # From flask uploading tutorial: http://flask.pocoo.org/docs/0.12/patterns/fileuploads/
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #TODO:
            #return redirect(url_for('uploaded_file', filename=filename))
            result = {'result': 'Success'}
            return jsonify(result)
        else:
            # return error
            result = {'result': 'Failure'}
            return jsonify(result)

api.add_resource(Employees, '/employees') # Route_1
api.add_resource(Tracks, '/tracks') # Route_2
api.add_resource(Employees_Name, '/employees/<employee_id>') # Route_3
api.add_resource(UploadFile, '/upload') # Route 4

if __name__ == '__main__':
     app.run(port='5010')