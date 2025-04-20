from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        user=os.environ.get('DB_USER', 'root'),
        password=os.environ.get('DB_PASSWORD', '62221085'),
        database=os.environ.get('DB_NAME', 'mis_gapms')
    )

@app.route('/api/student/<application_id>', methods=['GET'])
def get_student_info(application_id):
    try:
        db_conn = get_db_connection()
        cur = db_conn.cursor(dictionary=True)
        
        # Get student info from application_data
        cur.execute("""
            SELECT * FROM application_data 
            WHERE application_id = %s
        """, (application_id,))
        student_info = cur.fetchone()
        
        if not student_info:
            return jsonify({"error": "Student not found"}), 404
            
        # Get courses
        cur.execute("""
            SELECT course_name, credits, grade 
            FROM courses 
            WHERE application_id = %s
        """, (application_id,))
        courses = cur.fetchall()
        
        response = {
            "student_info": student_info,
            "courses": courses
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'db_conn' in locals():
            db_conn.close()

@app.route('/api/update-status', methods=['POST'])
def update_student_status():
    try:
        data = request.get_json()
        application_id = data.get('application_id')
        new_status = data.get('status')
        
        if not application_id or not new_status:
            return jsonify({"error": "Missing required fields"}), 400
            
        db_conn = get_db_connection()
        cur = db_conn.cursor()
        
        cur.execute("""
            UPDATE application_data 
            SET student_status = %s 
            WHERE application_id = %s
        """, (new_status, application_id))
        
        db_conn.commit()
        return jsonify({"message": "Status updated successfully"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cur' in locals():
            cur.close()
        if 'db_conn' in locals():
            db_conn.close()

def handler(event, context):
    """Netlify serverless function handler"""
    with app.request_context(event):
        return app.dispatch_request()

if __name__ == '__main__':
    app.run() 