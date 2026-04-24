import os

import mysql.connector


def get_db():
    return mysql.connector.connect(
        host=os.environ.get("MYSQL_HOST", "127.0.0.1"),
        port=int(os.environ.get("MYSQL_PORT", "3306")),
        user=os.environ.get("MYSQL_USER", "root"),
        password=os.environ.get("MYSQL_PASSWORD", ""),
        database=os.environ.get("MYSQL_DATABASE", "farming_monitor"),
        autocommit=False,
    )


def ensure_schema():
    """
    Safety net: create table if it doesn't exist.
    Keep schema.sql as the source of truth; this is only for quick start.
    """
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              name VARCHAR(100) NOT NULL,
              email VARCHAR(255) NOT NULL,
              role ENUM('admin','farmer') NOT NULL DEFAULT 'farmer',
              password_hash VARCHAR(255) NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_users_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        # If the table existed from an earlier version, make sure role exists.
        cur.execute("SHOW COLUMNS FROM users LIKE 'role'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE users ADD COLUMN role ENUM('admin','farmer') NOT NULL DEFAULT 'farmer' AFTER email")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              farmer_id BIGINT UNSIGNED NOT NULL,
              title VARCHAR(200) NOT NULL,
              description TEXT NULL,
              status ENUM('pending','done') NOT NULL DEFAULT 'pending',
              assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_tasks_farmer (farmer_id),
              CONSTRAINT fk_tasks_farmer FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        # If tasks existed from an earlier version, drop due_date if present.
        cur.execute("SHOW COLUMNS FROM tasks LIKE 'due_date'")
        if cur.fetchone() is not None:
            cur.execute("ALTER TABLE tasks DROP COLUMN due_date")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              farmer_id BIGINT UNSIGNED NOT NULL,
              subject VARCHAR(200) NOT NULL,
              message TEXT NOT NULL,
              status ENUM('open','approved','rejected') NOT NULL DEFAULT 'open',
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              KEY idx_requests_farmer (farmer_id),
              KEY idx_requests_status (status),
              CONSTRAINT fk_requests_farmer FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              farmer_id BIGINT UNSIGNED NOT NULL,
              seed_type VARCHAR(120) NOT NULL,
              quantity INT NOT NULL DEFAULT 0,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_inventory_farmer_seed (farmer_id, seed_type),
              CONSTRAINT fk_inventory_farmer FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS farm_status (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
              farmer_id BIGINT UNSIGNED NOT NULL,
              health ENUM('good','needs_treatment') NOT NULL DEFAULT 'good',
              crop_type VARCHAR(120) NOT NULL DEFAULT '',
              moisture_percent INT NOT NULL DEFAULT 0,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_farm_status_farmer (farmer_id),
              CONSTRAINT fk_farm_status_farmer FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        # If farm_status existed from an earlier version, migrate columns.
        cur.execute("SHOW COLUMNS FROM farm_status LIKE 'health'")
        if cur.fetchone() is None:
            cur.execute(
                "ALTER TABLE farm_status ADD COLUMN health ENUM('good','needs_treatment') NOT NULL DEFAULT 'good' AFTER farmer_id"
            )
        cur.execute("SHOW COLUMNS FROM farm_status LIKE 'moisture_percent'")
        if cur.fetchone() is None:
            cur.execute("ALTER TABLE farm_status ADD COLUMN moisture_percent INT NOT NULL DEFAULT 0 AFTER crop_type")
        cur.execute("SHOW COLUMNS FROM farm_status LIKE 'last_irrigation_date'")
        if cur.fetchone() is not None:
            cur.execute("ALTER TABLE farm_status DROP COLUMN last_irrigation_date")
        cur.execute("SHOW COLUMNS FROM farm_status LIKE 'last_seeding_date'")
        if cur.fetchone() is not None:
            cur.execute("ALTER TABLE farm_status DROP COLUMN last_seeding_date")
        cur.execute("SHOW COLUMNS FROM farm_status LIKE 'notes'")
        if cur.fetchone() is not None:
            cur.execute("ALTER TABLE farm_status DROP COLUMN notes")
        conn.commit()
    finally:
        conn.close()
