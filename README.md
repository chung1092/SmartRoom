# Face Recognition System

A Flask web application for face recognition using OpenCV and face_recognition library.

## Features

- Add new faces to the database
- Recognize faces from uploaded images
- Simple authentication system
- SQLite database for storing face data

## Requirements

- Python 3.7+
- OpenCV
- face_recognition library
- Flask
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd face-recognition-system
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the Flask application:
```bash
python run.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Login with the default credentials:
   - Username: admin
   - Password: admin123

4. Use the application to:
   - Add new faces by uploading images and providing names
   - Recognize faces by uploading images containing faces

## Project Structure

```
app/
├── __init__.py      # Flask app initialization
├── views.py         # Main routes and views
├── auth.py          # Authentication routes
├── main.py          # Core functionality and database models
├── templates/       # HTML templates
└── static/         # Static files (CSS, JS, uploaded images)
```

## Security Note

This is a basic implementation. For production use:
- Use proper user authentication
- Implement secure password hashing
- Add input validation
- Use environment variables for sensitive data
- Implement proper error handling 