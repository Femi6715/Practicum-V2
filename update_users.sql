-- Modify the users table to match registration form fields
ALTER TABLE users
MODIFY COLUMN role ENUM('Applicant','Admin','Reviewer') DEFAULT 'Applicant',
MODIFY COLUMN status ENUM('Pending','Admitted','Rejected') DEFAULT 'Pending'; 