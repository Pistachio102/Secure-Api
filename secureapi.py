from flask import Flask, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager

from werkzeug.utils import secure_filename
import os

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'

# Setup the Flask-JWT-Simple extension
app.config['JWT_SECRET_KEY'] = 'super_secret_for_generating_jwt'  # Change this!
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


jwt = JWTManager(app)

USER='eyenuk'
PASSWD='eyenuk'

#ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
ALLOWED_EXTENSIONS = set(['pdf','png', 'jpg', 'jpeg'])

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# Provide a method to create access tokens. The create_jwt()
# function is used to actually generate the token
@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    params = request.get_json()
    username = params.get('username', None) 
    password = params.get('password', None) 

    if not username:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400

    if username != USER or password != PASSWD:
        return jsonify({"msg": "Bad username or password"}), 401

    # Identity can be any data that is json serializable
    access_token = {'jwt': create_access_token(identity=username)}
    return jsonify(access_token), 200


# Protect a view with jwt_required, which requires a valid jwt
# to be present in the headers.

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    return jsonify({'user': get_jwt_identity()}), 200

@app.route("/upload", methods=["POST"])
@jwt_required()
def upload():
    ref_no = request.form['ref_no']
    uploaded_files = request.files.getlist('file[]')

    success=False

    if len(uploaded_files)==5 and ref_no!=None:

        for file in uploaded_files:
            if file and allowed_file(file.filename):       
                
                success=True
            else:
                success=False
                break
    else:
        success=False
    
    if success:
        for file in uploaded_files:
            filename = secure_filename(file.filename)
            print(filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
           
    
    return jsonify({'success': success, 'ref_no': ref_no}), 200    
    #return jsonify({'client id': ref_no,'Received Files': msg}), 200        
    
    

    
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run()


