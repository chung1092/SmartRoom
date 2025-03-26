from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from .models import Account, db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        account = Account.query.filter_by(username=username).first()
        if account and account.check_password(password):
            session['logged_in'] = True
            session['user_id'] = account.id
            print('Logged in successfully!')
            return redirect(url_for('view.index'))
        else:
            print('Invalid credentials')
    
    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    return redirect(url_for('auth.login')) 