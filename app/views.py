import traceback
import chardet
from .models import Class, distance_face
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
from sqlalchemy import inspect, text
import subprocess



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

@view.route('/add_class_file', methods=['POST'])
def add_class_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy file!"})
    file = request.files['file']
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file, encoding="utf-8", dtype=str)
        elif file.filename.endswith('.xlsx'):
            df = pd.read_excel(file, dtype=str)
        else:
            return jsonify({"success": False, "message": "Chỉ chấp nhận file .xlsx hoặc .csv!"})
        
        df.columns = df.columns.str.strip().str.lower()
        required_columns = {"name"}
        if not required_columns.issubset(df.columns):
            return jsonify({"success": False, "message": "File thiếu cột 'name'!"})
        df.rename(columns={"name": "class_name"}, inplace=True)
        added_count = 0
        for _, row in df.iterrows():
            try:
                class_name = str(row["class_name"]).strip()
                if not class_name or class_name.lower() == 'nan':
                    continue
                existing_class = Class.query.filter_by(class_name=class_name).first()
                if existing_class:
                    continue
                _class = Class(
                    class_name=class_name,
                    number_of_student=0
                )
                db.session.add(_class)
                added_count += 1
            except Exception as e:
                raise e
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"success": False, "message": f"Lỗi khi lưu vào database: {str(e)}"})
        message = f"Thêm {added_count} lớp thành công!" if added_count > 0 else "Không có lớp mới nào được thêm vào!"
        return jsonify({"success": True, "message": message})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Lỗi khi lưu vào database: {str(e)}"})

@view.route('/add_student_file', methods=['POST'])
def add_student_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Không tìm thấy file!"})
    
    file = request.files['file']
    if file.filename.endswith('.csv'):
        df = pd.read_csv(file, encoding="utf-8", dtype=str)
    elif file.filename.endswith('.xlsx'):
        df = pd.read_excel(file, header=None, dtype=str)
    else:
        return jsonify({"success": False, "message": "Chỉ chấp nhận file .xlsx hoặc .csv!"})
    
    class_name = df.iloc[0, 0]
    df.columns = df.iloc[1].astype(str).str.strip().str.lower()
    df = df.iloc[2:].reset_index(drop=True)
    print(class_name)
    required_columns = {"name", "code", "identifier", "phone", "email", "gender"}
    if not required_columns.issubset(df.columns):
        return jsonify({"success": False, "message": "File thiếu các cột bắt buộc!"})
    df.rename(columns={
        "name": "full_name",
        "code": "student_code",
        "identifier": "student_identifier",
        "phone": "phone",
        "email": "email",
        "gender": "gender",
        "birth": "date_of_birth"
    }, inplace=True)
    try:
        class_id = None
        for _class in Class.query.all():
            if _class.class_name == class_name:
                class_id = _class.class_id
                break
        if class_id is None:
            return jsonify({"success": False, "message": "Lớp không tồn tại!"})
        inserted = 0
        for _, row in df.iterrows():
            existing_student = db.session.query(Student).filter_by(student_code=row["student_code"]).first()
            if existing_student:
                continue
            student = Student(
                full_name=row["full_name"] if pd.notna(row["full_name"]) else None,
                student_code=row["student_code"] if pd.notna(row["student_code"]) else None,
                student_identifier=row["student_identifier"] if pd.notna(row["student_identifier"]) else None,
                class_id=class_id,
                gender=1 if str(row["gender"]).strip().lower() in ["nam", "male"] else 
                       0 if str(row["gender"]).strip().lower() in ["nữ", "female"] else None,
                email=row["email"] if pd.notna(row["email"]) else None,
                phone=str(row["phone"]) if pd.notna(row["phone"]) else None,
                date_of_birth=pd.to_datetime(row["date_of_birth"], errors='coerce').date() if pd.notna(row["date_of_birth"]) else None,
            )
            if student.phone is not None and student.phone[0] == "'":
                student.phone = "0" + student.phone[1:]
            elif student.phone is not None and student.phone[0] != "0":
                student.phone = "0" + student.phone
            if student.student_identifier is not None and student.student_identifier[0] == "'":
                student.student_identifier = "0" + student.student_identifier[1:]
            elif student.student_identifier is not None and student.student_identifier[0] != "0":
                student.student_identifier = "0" + student.student_identifier
            db.session.add(student)
            inserted += 1
        db.session.query(Class).filter_by(class_id=class_id).update({"number_of_student": Class.number_of_student + inserted})
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Lỗi khi lưu vào database: {str(e)}"})
    return jsonify({"success": True, "message": "Thêm sinh viên thành công!"})

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
        return jsonify({"success": False, "message": message})
        
@view.route('/recognize', methods=['GET', 'POST'])
def recognize():
    global name
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
        image_array = np.array(image)
        face_encodings = face_recognition.face_encodings(image_array)
        if not face_encodings:
            return render_template('recognize.html')
        results = distance_face(face_encodings)
        student = results[0]
        joined_names = " và ".join([r.full_name for r in results])
        if joined_names == "Không xác định":
            message = "Không xác định"
            student.full_name = "Không xác định"
        else:
            message = f"Xin chào! {joined_names}."
            for class_ in Class.query.all():
                if class_.class_id == student.class_id:
                    class_name = class_.class_name
                    break
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close()
        tts = gTTS(text=message, lang='vi')
        tts.save(temp_file.name)
        subprocess.Popen(["start", temp_file.name], shell=True)
        student_data = {
            "student_id": student.student_id,
            "full_name": student.full_name,
            "student_code": student.student_code,
            "student_identifier": student.student_identifier,
            "email": student.email if student.email else "NULL",
            "gender": "Nam" if student.gender == 1 else "Nữ",
            "class_name": class_name,
            "phone": student.phone if student.phone else "NULL",
            "image_path": student.image_path if student.image_path else "NULL",
        }
        os.remove(temp_file.name)
        return jsonify({"success": True, "student": student_data})
    return jsonify({"success": False, "message": "Lỗi tải ảnh lên"})

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
            results = distance_face(face_encodings)
            student = results[0]
            if joined_names == "Không xác định":
                message = "Không xác định"
                student.full_name = "Không xác định"

            else:
                message = f"Xin chào! {joined_names}."
                for class_ in Class.query.all():
                    if class_.class_id == student.class_id:
                        class_name = class_.class_name
                        break
            joined_names = " và ".join([r.full_name for r in results])
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_file.close()
            tts = gTTS(text=message, lang='vi')
            tts.save(temp_file.name)
            subprocess.Popen(["start", temp_file.name], shell=True)
            student_data = {
                "student_id": student.student_id,
                "full_name": student.full_name,
                "student_code": student.student_code,
                "student_identifier": student.student_identifier,
                "email": student.email if student.email else "NULL",
                "gender": "Nam" if student.gender == 1 else "Nữ",
                "class_name": class_name,
                "phone": student.phone if student.phone else "NULL",
                "image_path": student.image_path if student.image_path else "NULL",
            }
            os.remove(temp_file.name)
            return jsonify({"success": True, "student": student_data})
        except Exception as e:
            return jsonify({"success": False, "message": f"Lỗi xử lý: {str(e)}"})
    return jsonify({"message": "Lỗi up video!", "success": False})

@view.route('/recognize_camera', methods=['GET', 'POST'])
def recognize_camera():
    if request.method == 'GET':
        return render_template('recognize_camera.html')
    
@view.route('/student_mng', methods=['GET', 'POST'])
def student_mng():
    inspector = inspect(db.engine)
    if not inspector.has_table("Tbl_students"):
        Student.__table__.create(db.engine)
    students = Student.query.all()
    if not inspector.has_table("Tbl_class"):
        Class.__table__.create(db.engine)
    _class = Class.query.filter(Class.number_of_student > 0).all()
    return render_template('student_mng.html', students=students, _class = _class)

@view.route("/filter_students", methods=["POST"])
def filter_students():
    data = request.get_json()
    class_id = int(data.get("class_id"))
    if class_id != 0:
        students = Student.query.filter_by(class_id=class_id).all()
        student_list = [{
            "student_id": student.student_id,
            "full_name": student.full_name,
            "student_code": student.student_code,
            "student_identifier": student.student_identifier,
            "class_id": student.class_id,
            "gender": student.gender,
            "email": student.email,
            "phone": student.phone,
            "face_encoding": bool(student.face_encoding)
        } for student in students]
    else:
        students = Student.query.all()
        student_list = [{
            "student_id": student.student_id,
            "full_name": student.full_name,
            "student_code": student.student_code,
            "student_identifier": student.student_identifier,
            "class_id": student.class_id,
            "gender": student.gender,
            "email": student.email,
            "phone": student.phone,
            "face_encoding": bool(student.face_encoding)
        } for student in students]
    return jsonify({"success": True, "students": student_list})

@view.route('/class_mng', methods=['GET'])
def class_mng():
    inspector = inspect(db.engine)
    if not inspector.has_table("Tbl_class"):
        Class.__table__.create(db.engine)
    _class = Class.query.all()
    return render_template('class_mng.html', _class=_class)


@view.route('/room_allocation_exam', methods=['GET'])
def room_allocation_exam():
    return render_template('room_allocation_exam.html')



    