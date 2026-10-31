-- In the MySQL command line, run:
--   SOURCE C:/Users/rango/OneDrive/Desktop/MD-DRONE/MD-DRONE/MD-DRONE/backend/sql/mysql_setup.sql;
-- Replace the account/host below with the account used by the Flask backend.

CREATE DATABASE IF NOT EXISTS drone_forensics
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE drone_forensics;

-- The legacy Flask backend already uses the `cases` table. This creates it only
-- for a fresh database; existing case records and columns are kept intact.
CREATE TABLE IF NOT EXISTS cases (
  case_id INT NOT NULL AUTO_INCREMENT,
  case_number VARCHAR(64) NOT NULL,
  case_title VARCHAR(200) NOT NULL,
  description TEXT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'Open',
  examiner_name VARCHAR(150) NULL,
  investigation_date DATE NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (case_id),
  UNIQUE KEY uq_cases_case_number (case_number),
  KEY ix_cases_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
  user_id INT NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional command-line account for the Flask app. Set a strong password before
-- executing these statements, or use an existing MySQL account instead.
-- CREATE USER IF NOT EXISTS 'drone_app'@'localhost' IDENTIFIED BY 'CHANGE_THIS_PASSWORD';
-- GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX
--   ON drone_forensics.* TO 'drone_app'@'localhost';
-- FLUSH PRIVILEGES;
