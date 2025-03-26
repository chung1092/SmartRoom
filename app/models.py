from . import db
import face_recognition
import numpy as np
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Account(db.Model):
    __tablename__ = 'Accounts'  # Specify the exact table name from SQL Server
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)  # Changed from password_hash to password

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return self.password.split() == password.split()

class Face(db.Model):
    __tablename__ = 'Faces'  # Specify the exact table name from SQL Server
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    face_encoding = db.Column(db.PickleType, nullable=False)
    image_path = db.Column(db.String(200), nullable=False)


def save_face(image_path, name):
    
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)
    
    if not face_encodings:
        return False, "No face found in the image"
    
    face_encoding = face_encodings[0]
    
    new_face = Face(
        name=name,
        face_encoding=face_encoding,
        image_path=image_path
    )
    
    db.session.add(new_face)
    db.session.commit()
    
    return True, "Face saved successfully"

def recognize_face(image_path):

    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)
    
    if not face_encodings:
        return False, "No face found in the image"
    
    known_faces = Face.query.all()
    
    results = []
    for face_encoding in face_encodings:
        matches = []
        for known_face in known_faces:

            if face_recognition.compare_faces([known_face.face_encoding], face_encoding)[0]:
                matches.append(known_face.name)
        
        if matches:
            results.append(matches[0])
        else:
            results.append("Unknown")
    
    return True, results 