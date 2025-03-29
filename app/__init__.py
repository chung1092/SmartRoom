from flask import Flask
from flask_sqlalchemy import SQLAlchemy

import os

db = SQLAlchemy()
def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'NVQDTHNVTTTPNTNNVQNTLNVC'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://sa:123456@VAN_CHUONG/SmartRoom?driver=ODBC+Driver+17+for+SQL+Server&charset=utf8'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    db.init_app(app)
    
    from .views import view
    from .auth import auth
    
    app.register_blueprint(view)
    app.register_blueprint(auth)
    
    return app 