from . import db
import face_recognition
from gtts import gTTS
import time
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, Integer, String, Boolean, Float, Identity, LargeBinary, Text, PickleType
from sqlalchemy.ext.declarative import declarative_base

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
        return f'<Student {self.name}>'

def save_face(image_path, id):
    try:
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
    except Exception as e:
        db.session.rollback()
        return False, str(e)


def recognize_face(image_path):
    try:
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)
        if not face_encodings:
            return False, "No face found in the image"
        known_faces = Student.query.all()
        results = []
        for face_encoding in face_encodings:
            matches = []
            for known_face in known_faces:
                if known_face.face_encoding is None:
                    continue  # Bỏ qua nếu không có dữ liệu
                if face_recognition.compare_faces([known_face.face_encoding], face_encoding)[0]:
                    matches.append(known_face)
            if matches:
                results.append(matches[0])
            else:
                results.append(Student(name="Không nhận diện được khuôn mặt"))
        joined_names = results[0].name
        message = f"Xin chào! {joined_names}."
        tts = gTTS(text=message, lang='vi')
        filename = "temp_speech.mp3"
        tts.save(filename)
        os.system(f"start {filename}")
        time.sleep(1)
        os.remove(filename)
        return True, results
    except Exception as e:
        print(str(e))
        return False, str(e) 