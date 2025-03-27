from . import db
import face_recognition
import os
from werkzeug.security import generate_password_hash
from sqlalchemy import Column, Integer, String, Boolean,Identity
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import PickleType
from datetime import datetime


Base = declarative_base()

class Account(db.Model):
    __tablename__ = 'Accounts'  
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)  

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return self.password.split() == password.split()

class Student(db.Model):
    __tablename__ = 'Student'
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    from sqlalchemy import Unicode
    name = Column(Unicode(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    student_code = Column(String(20), unique=True, nullable=False)
    student_identifier = Column(String(20), unique=True, nullable=False)
    face_encoding = Column(PickleType, nullable=True)
    image_path = Column(String(200), nullable=True)
    status = Column(Boolean, default=False)

    def __repr__(self):
        return f'<Student {self}>'


def save_face(image_path, id):
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)

    if not face_encodings:
        return False, "No face found in the image"
    
    face_encoding = face_encodings[0]

    student = Student.query.get(id)
    if student is None:
        return False, f"Student with id {id} not found"
    
    filename = os.path.basename(image_path)
    student.face_encoding = face_encoding  
    student.image_path = os.path.join("static/uploads/", filename)
    student.status = True
    db.session.commit()
    return True, "Face encoding updated successfully"


     