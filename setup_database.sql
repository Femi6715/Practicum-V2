-- Create files table if it doesn't exist
CREATE TABLE IF NOT EXISTS files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id VARCHAR(255) NOT NULL UNIQUE,
    file_name VARCHAR(255),
    file_path VARCHAR(255),
    file_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create application_data table if it doesn't exist
CREATE TABLE IF NOT EXISTS application_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    application_id VARCHAR(255) NOT NULL,
    student_status VARCHAR(50),
    field_of_study VARCHAR(50),
    program_format VARCHAR(50),
    start_semester VARCHAR(50),
    start_year VARCHAR(4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES files(application_id)
); 