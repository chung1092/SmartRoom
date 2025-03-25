from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from werkzeug.utils import secure_filename
import os
from .models import save_face, recognize_face
from . import db
import face_recognition
import numpy as np
from PIL import Image
import io

view = Blueprint('view', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@view.route('/')
def index():
    return render_template('index.html')

@view.route('/add_face', methods=['GET', 'POST'])
def add_face():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        name = request.form.get('name')
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if not name:
            flash('Please enter a name')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            success, message = save_face(filepath, name)
            flash(message)
            
            if success:
                return redirect(url_for('view.index'))
            else:
                os.remove(filepath)
    
    return render_template('add_face.html')

@view.route('/recognize', methods=['GET', 'POST'])
def recognize():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):

            image_data = file.read()
            image = Image.open(io.BytesIO(image_data))
            
            image_array = np.array(image)
            
            face_encodings = face_recognition.face_encodings(image_array)
            
            if not face_encodings:
                flash("No face found in the image")
                return render_template('recognize.html')
            
            from .models import Face
            known_faces = Face.query.all()
            
            results = []
            for face_encoding in face_encodings:

                face_distances = []
                for known_face in known_faces:
                    distance = face_recognition.face_distance([known_face.face_encoding], face_encoding)[0]
                    face_distances.append((known_face.name, distance))
                
                face_distances.sort(key=lambda x: x[1])
                
                if face_distances and face_distances[0][1] < 0.6:
                    results.append(face_distances[0][0])
                else:
                    results.append("Unknown")
            from gtts import gTTS
            import os
            import time

            joined_names = " và ".join(results)
            text = f"Xin chào! {joined_names}."
            tts = gTTS(text=text, lang='vi')

            filename = "temp_speech.mp3"
            tts.save(filename)

            os.system(f"start {filename}")

            time.sleep(1)
            os.remove(filename)
            return render_template('recognize.html', results=results)
    
    return render_template('recognize.html') 