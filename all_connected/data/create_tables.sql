USE snapngo_db;


CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(50),
    `name` VARCHAR(50),
    compensation DECIMAL(4,2) DEFAULT 0,
    reliability DECIMAL(4,2) DEFAULT 0,
    PRIMARY KEY (id)
)
ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS tasks (
    id INT AUTO_INCREMENT,
    `location` VARCHAR(100),
    `description` VARCHAR(100),
    start_time DATETIME,
    `time_window` INT(3),
    deadline DATETIME,
    compensation DECIMAL(4,2),
    expired BOOLEAN,
    PRIMARY KEY (id)
)
ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS assignments (
    task_id INT,
    user_id VARCHAR(15),
    recommend_time DATETIME,
    img VARCHAR(100),
    submission_time DATETIME,
    status ENUM('not assigned','accepted','rejected','pending') DEFAULT 'not assigned',
    PRIMARY KEY (task_id, user_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
        ON UPDATE CASCADE
        ON DELETE CASCADE
)
ENGINE = InnoDB;
    
