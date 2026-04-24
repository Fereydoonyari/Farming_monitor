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
              password_hash VARCHAR(255) NOT NULL,
              created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_users_email (email)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
        conn.commit()
    finally:
        conn.close()
