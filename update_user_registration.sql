-- Add first_name and last_name columns to user_registration table
ALTER TABLE user_registration
ADD COLUMN first_name VARCHAR(100) AFTER id,
ADD COLUMN last_name VARCHAR(100) AFTER first_name; 