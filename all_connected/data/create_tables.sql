DROP DATABASE IF EXISTS `snapngo_with_ai_db`;
CREATE DATABASE `snapngo_with_ai_db`;


USE `snapngo_with_ai_db`;

DROP TABLE IF EXISTS `assignments`;
DROP TABLE IF EXISTS `users`;
DROP TABLE IF EXISTS `tasks`;

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50),
    `name` VARCHAR(50),
    compensation DECIMAL(4,2) DEFAULT 0,
    reliability DECIMAL(4,2) DEFAULT 0.5,
    `status` ENUM('active', 'inactive') DEFAULT 'active',
    PRIMARY KEY (id)
)
ENGINE = InnoDB;


CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT,
    `location` VARCHAR(100),
    `description` VARCHAR(500),
    task_type ENUM('data_collection', 'verification') DEFAULT 'data_collection',
    assignment_id INT,
    start_time DATETIME,
    time_window INT(3),
    compensation DECIMAL(4,2) DEFAULT 0,
    expired BOOLEAN,
    PRIMARY KEY (id)
)
ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS assignments (
    id INT AUTO_INCREMENT,
    task_id INT,
    user_id VARCHAR(15),
    recommend_time DATETIME,
    img varchar(300),
    submission_time DATETIME,
    gemini_decision BOOLEAN,
    gemini_explanation TEXT,
    verified_at DATETIME,
    verified_count INT DEFAULT 0,
    `status` ENUM('not assigned','accepted','rejected','pending') DEFAULT 'not assigned',
    PRIMARY KEY (id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
)
ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS user_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assignment_id INT,
    user_id VARCHAR(50),
    feedback_task_id INT,
    gemini_decision BOOLEAN,
    user_agrees BOOLEAN,
    user_comment TEXT,
    compensation DECIMAL(4,2) DEFAULT 0.25,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (assignment_id) REFERENCES assignments(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (feedback_task_id) REFERENCES tasks(id)
)
ENGINE = InnoDB;

    
