import mysql.connector

# Connect to the database
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='62221085',
    database='mis_gapms'
)

# Create a cursor
cur = conn.cursor()

# Modify the users table
cur.execute("""
    ALTER TABLE users
    MODIFY COLUMN role ENUM('Applicant','Admin','Reviewer') DEFAULT 'Applicant',
    MODIFY COLUMN status ENUM('Pending','Admitted','Rejected') DEFAULT 'Pending'
""")

# Commit the changes
conn.commit()

# Close the connection
cur.close()
conn.close()

print("Users table modified successfully!") 