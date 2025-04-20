from flask import Blueprint, request, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re

auth = Blueprint('auth', __name__)

# Database connection function
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='62221085',
        database='mis_gapms'
    )

# Email validation function
def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth.route('/register/basic', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['username', 'email', 'password', 'first_name', 'last_name']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    username = data['username'].strip()
    email = data['email'].strip()
    password = data['password']
    first_name = data['first_name'].strip()
    last_name = data['last_name'].strip()
    
    # Validate input
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters long'}), 400
    
    if not is_valid_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Check if username or email already exists
        cur.execute('SELECT id FROM user_registration WHERE username = %s OR email = %s', 
                   (username, email))
        if cur.fetchone():
            return jsonify({'error': 'Username or email already exists'}), 400
        
        # Hash password and insert new user
        hashed_password = generate_password_hash(password)
        cur.execute('''
            INSERT INTO user_registration 
            (username, email, password, first_name, last_name) 
            VALUES (%s, %s, %s, %s, %s)
        ''', (username, email, hashed_password, first_name, last_name))
        conn.commit()
        
        return jsonify({'message': 'Registration successful'}), 201
        
    except Exception as e:
        print(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

@auth.route('/signin/basic', methods=['POST'])
def signin():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['username', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    username = data['username'].strip()
    password = data['password']
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Get user by username
        cur.execute('SELECT * FROM user_registration WHERE username = %s', (username,))
        user = cur.fetchone()
        
        if not user or not check_password_hash(user['password'], password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Create session data
        session_data = {
            'user_id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
        
        return jsonify(session_data), 200
        
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close() 