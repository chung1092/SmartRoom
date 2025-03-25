from flask import Blueprint, render_template, redirect, url_for, flash, request, session

auth = Blueprint('auth', __name__)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            flash('Logged in successfully!')
            return redirect(url_for('view.index'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Logged out successfully!')
    return redirect(url_for('auth.login')) 