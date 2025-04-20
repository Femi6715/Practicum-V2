import mysql.connector

def update_user_registration_table():
    try:
        # Connect to the database
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='62221085',
            database='mis_gapms'
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Add first_name and last_name columns
        cur.execute("""
            ALTER TABLE user_registration
            ADD COLUMN first_name VARCHAR(100) AFTER id,
            ADD COLUMN last_name VARCHAR(100) AFTER first_name
        """)
        
        # Commit the changes
        conn.commit()
        print("Successfully added first_name and last_name columns to user_registration table")
        
    except Exception as e:
        print(f"Error updating user_registration table: {str(e)}")
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    update_user_registration_table() 