import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import ensure_schema, get_db


load_dotenv()


def create_app():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    ensure_schema()

    @app.get("/")
    def home():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/app")
    def app_page():
        return send_from_directory(app.static_folder, "app.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    @app.post("/api/register")
    def register():
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not name or not email or not password:
            return jsonify({"error": "name, email, password are required"}), 400

        password_hash = generate_password_hash(password)

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return jsonify({"error": "email already registered"}), 409

            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, password_hash),
            )
            conn.commit()
            user_id = cur.lastrowid

            session["user_id"] = int(user_id)
            return jsonify({"id": int(user_id), "name": name, "email": email}), 201
        finally:
            conn.close()

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, password_hash FROM users WHERE email=%s",
                (email,),
            )
            user = cur.fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                return jsonify({"error": "invalid credentials"}), 401

            session["user_id"] = int(user["id"])
            return jsonify({"id": int(user["id"]), "name": user["name"], "email": user["email"]})
        finally:
            conn.close()

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/me")
    def me():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "not authenticated"}), 401

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, name, email, created_at FROM users WHERE id=%s", (user_id,))
            user = cur.fetchone()
            if not user:
                session.clear()
                return jsonify({"error": "not authenticated"}), 401
            user["id"] = int(user["id"])
            user["created_at"] = user["created_at"].isoformat()
            return jsonify(user)
        finally:
            conn.close()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
