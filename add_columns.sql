ALTER TABLE application_data 
ADD COLUMN date_of_birth VARCHAR(20),
ADD COLUMN gender VARCHAR(20),
ADD COLUMN email VARCHAR(255),
ADD COLUMN phone VARCHAR(50),
ADD COLUMN address TEXT,
ADD COLUMN city VARCHAR(100),
ADD COLUMN state VARCHAR(100),
ADD COLUMN zip_code VARCHAR(20),
ADD COLUMN country VARCHAR(100),
ADD COLUMN is_us_resident BOOLEAN,
ADD COLUMN citizen_type VARCHAR(50),
ADD COLUMN military_service BOOLEAN,
ADD COLUMN university VARCHAR(255),
ADD COLUMN degree VARCHAR(100),
ADD COLUMN major VARCHAR(255),
ADD COLUMN gpa DECIMAL(3,2),
ADD COLUMN campus VARCHAR(50),
ADD COLUMN program VARCHAR(255),
ADD COLUMN enrollment_semester VARCHAR(50); 