import cv2
from flask import session
import numpy as np
from . import db
import face_recognition
import os
from werkzeug.security import generate_password_hash
from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Boolean,Identity, Text, Time, Unicode
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import PickleType
from datetime import datetime


Base = declarative_base()

class Class(db.Model):
    __tablename__ = 'Tbl_class'
    class_id = Column(Integer, primary_key=True)
    class_name = Column(Unicode(20), nullable=False)
    number_of_student = Column(Integer)

class Account(db.Model):
    __tablename__ = 'Tbl_accounts'
    account_id = Column(Integer, primary_key=True)
    username = Column(String(30), unique=True, nullable=False)
    password = Column(String(50), nullable=False) 

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return self.password.split() == password.split()
    
class Course(db.Model):
    __tablename__ = 'Tbl_courses'
    course_id = Column(Integer, primary_key=True)
    course_name = Column(String(100), nullable=False)

class Room(db.Model):
    __tablename__ = 'Tbl_rooms'
    room_id = Column(Integer, primary_key=True)
    room_name = Column(String(50))
    capacity = Column(Integer, nullable=False)

class Exam(db.Model):
    __tablename__ = 'Tbl_exams'
    exam_id = Column(Integer, primary_key=True)
    exam_time = Column(Time, nullable=False)
    duration = Column(Integer, nullable=False)

class ExamSchedule(db.Model):
    __tablename__ = 'Tbl_exam_schedule'
    exam_schedule_id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey('Tbl_exams.exam_id'), nullable=False)
    course_id = Column(Integer, ForeignKey('Tbl_courses.course_id'), nullable=False)
    room_id = Column(Integer, ForeignKey('Tbl_rooms.room_id'), nullable=False)
    exam_day = Column(Date)

class Student(db.Model):
    __tablename__ = 'Tbl_students'
    student_id = Column(Integer, primary_key=True)
    student_code = Column(String(20), nullable=False)
    student_identifier = Column(String(20), nullable=False)
    full_name = Column(Unicode(20), nullable=False)
    class_id = Column(Integer, ForeignKey('Tbl_class.class_id'), nullable=False)
    date_of_birth = Column(Date)
    gender = Column(Integer)
    email = Column(String(100))
    phone = Column(String(15))
    face_encoding = Column(PickleType)
    image_path = Column(String(200))

    def __repr__(self):
        return f'<Student {self}>'
    
class StudentExam(db.Model):
    __tablename__ = 'Tbl_student_exam'
    student_exam_id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('Tbl_students.student_id'), nullable=False)
    exam_schedule_id = Column(Integer, ForeignKey('Tbl_exam_schedule.exam_schedule_id'), nullable=False)
    test_score = Column(Float)

def distance_face(face_encodings):
    known_faces = Student.query.all()
    results = []
    for face_encoding in face_encodings:
            face_distances = []
            for known_face in known_faces:
                if known_face.face_encoding is None:
                    continue  
                distance = face_recognition.face_distance([known_face.face_encoding], face_encoding)[0]
                face_distances.append((known_face, distance))
            face_distances.sort(key=lambda x: x[1])
            if face_distances and face_distances[0][1] < 0.4:
                results.append(face_distances[0][0])
            else:
                results.append(Student(full_name="Không xác định"))
    return results

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


     