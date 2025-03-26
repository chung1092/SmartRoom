import time
import face_recognition
from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from gtts import gTTS
import numpy as np
from werkzeug.utils import secure_filename
import os
from .models import save_face
from . import db
from PIL import Image
import cv2
import io
import tempfile
import pandas as pd
from .models import Student
from sqlalchemy import inspect
import subprocess
import base64


view = Blueprint('view', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

@view.route('/')
def index():
    return render_template('index.html')

@view.route('/add_student', methods=['POST'])
def add_student():
        name = request.form.get('name')
        student_code = request.form.get('student_code')
        student_identifier = request.form.get('student_identifier')
        email = request.form.get('email')
        phone = request.form.get('phone')
        new_student = Student(
            name=name,
            student_code=student_code,
            student_identifier=student_identifier,
            email=email,
            phone=phone
        )
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('view.student_mng'))

@view.route('/add_student_file', methods=['POST'])
def add_student_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy file!"})
    
    file = request.files['file']
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file, dtype=str)
    elif file.filename.endswith('.xlsx'):
        df = pd.read_excel(file, dtype=str)
    else:
        return jsonify({"success": False, "message": "Chỉ chấp nhận file .xlsx hoặc .csv!"})
    df.columns = df.columns.str.strip().str.lower()

    required_columns = {"name", "code", "identifier", "phone", "mail"}
    if not required_columns.issubset(df.columns):
        return jsonify({"success": False, "message": "File thiếu các cột bắt buộc!"})
    
    df.rename(columns={
        "name": "name",
        "code": "student_code",
        "identifier": "student_identifier",
        "phone": "phone",
        "mail": "email"
    }, inplace=True)

    try:
        for _, row in df.iterrows():
            existing_student = db.session.query(Student).filter_by(student_code=row["student_code"]).first()
            if existing_student:
                continue
            student = Student(
                name=row["name"],
                student_code=row["student_code"],
                student_identifier=row["student_identifier"],
                phone=row["phone"],
                email=row["email"]
            )
            db.session.add(student)
        db.session.commit()
        
        # Check if this is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": True, "message": "Thêm sinh viên thành công!"})
        else:
            return redirect(url_for('view.student_mng'))
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Lỗi khi lưu vào database: {str(e)}"})

@view.route('/add_face', methods=['POST'])
def add_face():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy file."})
    file = request.files['file']
    student_id = request.form.get("student_id")
    if file.filename == '':
        return jsonify({"success": False, "message": "File không hợp lệ."})
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    success, message = save_face(filepath, student_id)
    if success:
        return jsonify({"success": success, "message": message})
    else:
        os.remove(filepath)

@view.route('/recognize', methods=['GET', 'POST'])
def recognize():
    if request.method == 'GET':
        return render_template('recognize.html')
    if 'file' not in request.files:
        return jsonify({"message": "Lỗi: Không tìm thấy file!", "success": False})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Lỗi: File không hợp lệ!", "success": False})
    if file and allowed_file(file.filename):
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))
        
        image_array = np.array(image     
)
        face_encodings = face_recognition.face_encodings(image_array)
        
        if not face_encodings:
            return render_template('recognize.html')
        
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

            if face_distances and face_distances[0][1] < 0.6:
                results.append(face_distances[0][0])
            else:
                results.append(Student(name="Không xác định"))

            joined_names = " và ".join([r.name for r in results])
            message = f"Xin chào! {joined_names}."
            
            joined_names = " và ".join([r.name for r in results])
            message = f"Xin chào! {joined_names}."
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()
            tts = gTTS(text=message, lang='vi')
            tts.save(temp_file.name)
            subprocess.Popen(["start", temp_file.name], shell=True)
            if results and isinstance(results[0], Student):
                student = results[0]
                student_data = {
                    "id": getattr(student, "id", "Không có ID"),
                    "name": getattr(student, "name", "Không có tên"),
                    "student_code": getattr(student, "student_code", "Không có mã SV"),
                    "email": getattr(student, "email", "Không có email"),
                    "phone": getattr(student, "phone", "Không có số điện thoại"),
                }
                time.sleep(2)
                try:
                    os.remove(temp_file.name)
                except:
                    pass
                return jsonify({"success": True, "student": student_data})
            else:
                return jsonify({"success": False, "message": "Không tìm thấy sinh viên"})

@view.route('/recognize_video', methods=['GET', 'POST'])
def recognize_video():
    if request.method == 'GET':
        return render_template('recognize_video.html')
    if 'video' not in request.files:
        print("Recognize video.")
        return jsonify({"message": "Lỗi: Không tìm thấy file!", "success": False})
    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({"message": "Lỗi: File không hợp lệ!", "success": False})
    if video_file and allowed_video_file(video_file.filename):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                video_file.save(temp_video.name)
                video_path = temp_video.name
            cap = cv2.VideoCapture(video_path)
            
            ret, frame = cap.read()
            if not ret:
                return render_template('recognize_video.html')
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_frame)
            
            if not face_encodings:
                return render_template('recognize_video.html')
            
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
                
                if face_distances and face_distances[0][1] < 0.6:
                    results.append(face_distances[0][0])
                else:
                    results.append(Student(name="Không xác định"))

            joined_names = " và ".join([r.name for r in results])
            message = f"Xin chào! {joined_names}."
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()
            tts = gTTS(text=message, lang='vi')
            tts.save(temp_file.name)
            subprocess.Popen(["start", temp_file.name], shell=True)
            if results and isinstance(results[0], Student):
                student = results[0]
                student_data = {
                    "id": getattr(student, "id", "Không có ID"),
                    "name": getattr(student, "name", "Không có tên"),
                    "student_code": getattr(student, "student_code", "Không có mã SV"),
                    "email": getattr(student, "email", "Không có email"),
                    "phone": getattr(student, "phone", "Không có số điện thoại"),
                }
                time.sleep(2)
                try:
                    os.remove(temp_file.name)
                except:
                    pass
                return jsonify({"success": True, "student": student_data})
            else:
                return jsonify({"success": False, "message": "Không tìm thấy sinh viên"})
        except Exception as e:
            return jsonify({"success": False, "message": f"Lỗi xử lý: {str(e)}"})

# @view.route('/recognize_camera', methods=['GET', 'POST'])
# def recognize_camera():
#     if request.method == 'GET':
#         return render_template('recognize_camera.html')
#     try:
#         # Lấy dữ liệu ảnh từ request
#         image_data = request.get_data()
#         image_data = image_data.split(b',')[1]  # Bỏ qua phần header của base64
#         image_bytes = base64.b64decode(image_data)
        
#         # Chuyển đổi bytes thành ảnh PIL
#         image = Image.open(io.BytesIO(image_bytes))
        
#         # Chuyển đổi PIL Image thành numpy array
#         image_array = np.array(image)
        
#         # Tìm khuôn mặt trong ảnh
#         face_encodings = face_recognition.face_encodings(image_array)
        
#         if not face_encodings:
#             return jsonify({'results': ["Không tìm thấy khuôn mặt"]})
        
#         known_faces = Student.query.all()
        
#         results = []
#         for i, face_encoding in enumerate(face_encodings):
#             # Tính khoảng cách với tất cả khuôn mặt đã biết
#             face_distances = []
#             for known_face in known_faces:
#                 distance = face_recognition.face_distance([known_face.face_encoding], face_encoding)[0]
#                 face_distances.append((known_face.name, distance))
            
#             # Sắp xếp theo khoảng cách (khoảng cách nhỏ hơn = khớp hơn)
#             face_distances.sort(key=lambda x: x[1])
            
#             # Sử dụng ngưỡng 0.6 (thấp hơn = chính xác hơn)
#             if face_distances and face_distances[0][1] < 0.6:
#                 name = face_distances[0][0]
#                 results.append(f"{name}:{i}")  # Thêm ID vào kết quả
#             else:
#                 results.append(f"Không nhận diện được:{i}")
        
#         # Chuyển văn bản thành giọng nói nếu có kết quả
#         if results:
#             names = [r.split(':')[0] for r in results if r.split(':')[0] != "Không nhận diện được"]
#             if names:
#                 joined_names = " và ".join(names)
#                 message = f"Xin chào! {joined_names}."
#                 temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
#                 temp_file.close()
#                 tts = gTTS(text=message, lang='vi')
#                 tts.save(temp_file.name)
#                 subprocess.Popen(["start", temp_file.name], shell=True)
#                 time.sleep(2)
#                 try:
#                     os.remove(temp_file.name)
#                 except:
#                     pass
#         return jsonify({'results': results})
        
#     except Exception as e:
#         print(f"Lỗi khi xử lý ảnh từ camera: {str(e)}")
#         return jsonify({'results': ["Có lỗi xảy ra khi xử lý ảnh"]})

@view.route('/student_mng', methods=['GET'])
def student_mng():
    inspector = inspect(db.engine)
    if not inspector.has_table("Student"):
        Student.__table__.create(db.engine)
    students = Student.query.all()
    return render_template('student_mng.html', students=students)