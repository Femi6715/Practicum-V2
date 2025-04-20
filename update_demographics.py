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

# Modify the student_demographics table to make gender nullable
cur.execute("""
    ALTER TABLE student_demographics
    MODIFY COLUMN gender ENUM('Male','Female','Other') NULL
""")

# Commit the changes
conn.commit()

# Close the connection
cur.close()
conn.close()

print("Student demographics table modified successfully!") 