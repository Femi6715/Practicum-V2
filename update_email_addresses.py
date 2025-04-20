import mysql.connector
import re
from app import extract_application_data, get_db_connection

def update_email_addresses():
    """Update email addresses in the application_data table"""
    print("Starting email address update process...")
    
    # Connect to the database
    db_conn = get_db_connection()
    cur = db_conn.cursor(dictionary=True)
    
    try:
        # Get all application records with their extracted text
        cur.execute("""
            SELECT ar.application_id, ad.extracted_text 
            FROM application_records ar
            LEFT JOIN application_data ad ON ar.application_id = ad.application_id
            WHERE ad.email = 'Unknown' OR ad.email IS NULL
        """)
        
        records = cur.fetchall()
        print(f"Found {len(records)} records to update")
        
        # Process each record
        for record in records:
            application_id = record['application_id']
            extracted_text = record['extracted_text']
            
            if not extracted_text:
                print(f"No extracted text for application_id {application_id}")
                continue
                
            # Extract application data including email
            app_data = extract_application_data(extracted_text)
            email = app_data.get('email', 'Unknown')
            
            if email != 'Unknown':
                # Update the email in the database
                cur.execute("""
                    UPDATE application_data 
                    SET email = %s 
                    WHERE application_id = %s
                """, (email, application_id))
                
                print(f"Updated email for application_id {application_id}: {email}")
            else:
                print(f"Could not extract email for application_id {application_id}")
        
        # Commit the changes
        db_conn.commit()
        print("Email address update completed successfully")
        
    except Exception as e:
        print(f"Error updating email addresses: {str(e)}")
        db_conn.rollback()
    finally:
        cur.close()
        db_conn.close()

if __name__ == "__main__":
    update_email_addresses() 