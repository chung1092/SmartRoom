from flask import Blueprint, render_template, request, redirect, url_for, current_app, jsonify
from werkzeug.utils import secure_filename
import os
from .models import save_face, recognize_face
from . import db
from PIL import Image
import io
import pandas as pd
from .models import Student
from sqlalchemy import inspect

view = Blueprint('view', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    return jsonify({"success": success, "message": message})

@view.route('/recognize', methods=['GET', 'POST'])
def recognize():
    if request.method == 'GET':
        return render_template('recognize.html')
    if 'file' not in request.files:
        return jsonify({"message": "Lỗi: Không tìm thấy file!", "success": False})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "Lỗi: File không hợp lệ!", "success": False})
    
    try:
        image_data = file.read()
        image = Image.open(io.BytesIO(image_data))

        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)

        temp_filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, temp_filename)
        image.save(filepath)

        success, results = recognize_face(filepath)
        try:
            os.remove(filepath)
        except:
            pass
            
        if not success:
            return jsonify({"message": results, "success": False})
        if results:
            student = results[0]
            student_data = {
                "id": student.id,
                "name": student.name,
                "student_code": student.student_code,
                "email": student.email,
                "phone": student.phone
            }
            return jsonify({"success": True, "student": student_data})

        return jsonify({"message": "Không tìm thấy sinh viên nào.", "success": False})
        
    except Exception as e:
        print(str(e))
        return jsonify({"message": f"Lỗi xử lý: {str(e)}", "success": False})

@view.route('/student_mng', methods=['GET'])
def student_mng():
    inspector = inspect(db.engine)
    if not inspector.has_table("Student"):
        Student.__table__.create(db.engine)
    students = Student.query.all()
    return render_template('student_mng.html', students=students)