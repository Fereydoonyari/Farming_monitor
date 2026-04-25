import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import ensure_schema, get_db


load_dotenv()


def create_app():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

    ensure_schema()

    @app.get("/")
    def home():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/app")
    def app_page():
        return send_from_directory(app.static_folder, "app.html")

    @app.get("/admin")
    def admin_page():
        return send_from_directory(app.static_folder, "admin.html")

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    def _require_auth():
        user_id = session.get("user_id")
        if not user_id:
            return None, (jsonify({"error": "not authenticated"}), 401)

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, name, email, role FROM users WHERE id=%s", (user_id,))
            user = cur.fetchone()
            if not user:
                session.clear()
                return None, (jsonify({"error": "not authenticated"}), 401)
            user["id"] = int(user["id"])
            return user, None
        finally:
            conn.close()

    def _require_admin():
        user, err = _require_auth()
        if err:
            return None, err
        if user["role"] != "admin":
            return None, (jsonify({"error": "admin only"}), 403)
        return user, None

    def _require_farmer():
        user, err = _require_auth()
        if err:
            return None, err
        if user["role"] != "farmer":
            return None, (jsonify({"error": "farmer only"}), 403)
        return user, None

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
                "INSERT INTO users (name, email, role, password_hash) VALUES (%s, %s, %s, %s)",
                (name, email, "farmer", password_hash),
            )
            conn.commit()
            user_id = cur.lastrowid

            session["user_id"] = int(user_id)
            return jsonify({"id": int(user_id), "name": name, "email": email, "role": "farmer"}), 201
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
                "SELECT id, name, email, role, password_hash FROM users WHERE email=%s",
                (email,),
            )
            user = cur.fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                return jsonify({"error": "invalid credentials"}), 401

            session["user_id"] = int(user["id"])
            return jsonify(
                {"id": int(user["id"]), "name": user["name"], "email": user["email"], "role": user["role"]}
            )
        finally:
            conn.close()

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/me")
    def me():
        user, err = _require_auth()
        if err:
            return err

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, name, email, role, created_at FROM users WHERE id=%s", (user["id"],))
            me_row = cur.fetchone()
            me_row["id"] = int(me_row["id"])
            me_row["created_at"] = me_row["created_at"].isoformat()
            return jsonify(me_row)
        finally:
            conn.close()

    # --------------------------
    # Farmer APIs (authenticated)
    # --------------------------
    @app.get("/api/farmer/tasks")
    def farmer_tasks():
        user, err = _require_farmer()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id, title, description, status, assigned_at
                FROM tasks
                WHERE farmer_id=%s
                ORDER BY assigned_at DESC, id DESC
                """,
                (user["id"],),
            )
            rows = cur.fetchall() or []
            for r in rows:
                r["id"] = int(r["id"])
                r["assigned_at"] = r["assigned_at"].isoformat()
            return jsonify(rows)
        finally:
            conn.close()

    @app.get("/api/farmer/requests")
    def farmer_requests():
        user, err = _require_farmer()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id, subject, message, status, created_at
                FROM requests
                WHERE farmer_id=%s
                ORDER BY created_at DESC, id DESC
                """,
                (user["id"],),
            )
            rows = cur.fetchall() or []
            for r in rows:
                r["id"] = int(r["id"])
                r["created_at"] = r["created_at"].isoformat()
            return jsonify(rows)
        finally:
            conn.close()

    @app.post("/api/farmer/requests")
    def farmer_create_request():
        user, err = _require_farmer()
        if err:
            return err
        data = request.get_json(silent=True) or {}
        subject = (data.get("subject") or "").strip()
        message = (data.get("message") or "").strip()
        if not subject or not message:
            return jsonify({"error": "subject and message are required"}), 400
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "INSERT INTO requests (farmer_id, subject, message) VALUES (%s, %s, %s)",
                (user["id"], subject, message),
            )
            conn.commit()
            return jsonify({"ok": True, "id": int(cur.lastrowid)}), 201
        finally:
            conn.close()

    @app.get("/api/farmer/inventory")
    def farmer_inventory():
        user, err = _require_farmer()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id, seed_type, quantity, updated_at
                FROM inventory
                WHERE farmer_id=%s
                ORDER BY seed_type ASC
                """,
                (user["id"],),
            )
            rows = cur.fetchall() or []
            for r in rows:
                r["id"] = int(r["id"])
                r["quantity"] = int(r["quantity"])
                r["updated_at"] = r["updated_at"].isoformat()
            return jsonify(rows)
        finally:
            conn.close()

    @app.post("/api/farmer/inventory")
    def farmer_upsert_inventory():
        user, err = _require_farmer()
        if err:
            return err
        data = request.get_json(silent=True) or {}
        seed_type = (data.get("seed_type") or "").strip()
        quantity = data.get("quantity")
        if not seed_type or quantity is None:
            return jsonify({"error": "seed_type and quantity are required"}), 400
        try:
            quantity_int = int(quantity)
        except Exception:
            return jsonify({"error": "quantity must be an integer"}), 400

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                INSERT INTO inventory (farmer_id, seed_type, quantity)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE quantity=VALUES(quantity)
                """,
                (user["id"], seed_type, quantity_int),
            )
            conn.commit()
            return jsonify({"ok": True})
        finally:
            conn.close()

    @app.put("/api/farmer/inventory/<int:item_id>")
    def farmer_update_inventory_item(item_id: int):
        user, err = _require_farmer()
        if err:
            return err
        data = request.get_json(silent=True) or {}
        quantity = data.get("quantity")
        if quantity is None:
            return jsonify({"error": "quantity is required"}), 400
        try:
            quantity_int = int(quantity)
        except Exception:
            return jsonify({"error": "quantity must be an integer"}), 400
        if quantity_int < 0:
            return jsonify({"error": "quantity must be >= 0"}), 400

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "UPDATE inventory SET quantity=%s WHERE id=%s AND farmer_id=%s",
                (quantity_int, item_id, user["id"]),
            )
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "inventory item not found"}), 404
            return jsonify({"ok": True})
        finally:
            conn.close()

    @app.delete("/api/farmer/inventory/<int:item_id>")
    def farmer_delete_inventory_item(item_id: int):
        user, err = _require_farmer()
        if err:
            return err

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("DELETE FROM inventory WHERE id=%s AND farmer_id=%s", (item_id, user["id"]))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "inventory item not found"}), 404
            return jsonify({"ok": True})
        finally:
            conn.close()

    @app.get("/api/farmer/farm-status")
    def farmer_get_farm_status():
        user, err = _require_farmer()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT id, health, crop_type, moisture_percent, updated_at
                FROM farm_status
                WHERE farmer_id=%s
                """,
                (user["id"],),
            )
            row = cur.fetchone()
            if not row:
                return jsonify(
                    {
                        "health": "good",
                        "crop_type": "",
                        "moisture_percent": 0,
                    }
                )
            row["id"] = int(row["id"])
            row["moisture_percent"] = int(row["moisture_percent"])
            row["updated_at"] = row["updated_at"].isoformat()
            return jsonify(row)
        finally:
            conn.close()

    @app.put("/api/farmer/farm-status")
    def farmer_update_farm_status():
        user, err = _require_farmer()
        if err:
            return err
        data = request.get_json(silent=True) or {}
        health = (data.get("health") or "").strip().lower()
        crop_type = (data.get("crop_type") or "").strip()
        moisture_percent = data.get("moisture_percent")

        if health not in ("good", "needs_treatment"):
            return jsonify({"error": "health must be good or needs_treatment"}), 400

        try:
            moisture_int = int(moisture_percent)
        except Exception:
            return jsonify({"error": "moisture_percent must be an integer"}), 400
        if moisture_int < 0 or moisture_int > 100:
            return jsonify({"error": "moisture_percent must be between 0 and 100"}), 400

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                INSERT INTO farm_status (farmer_id, health, crop_type, moisture_percent)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  health=VALUES(health),
                  crop_type=VALUES(crop_type),
                  moisture_percent=VALUES(moisture_percent)
                """,
                (user["id"], health, crop_type, moisture_int),
            )
            conn.commit()
            return jsonify({"ok": True})
        finally:
            conn.close()

    # --------------------------
    # Admin APIs (admin only)
    # --------------------------
    @app.get("/api/admin/farmers")
    def admin_farmers():
        _, err = _require_admin()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, created_at FROM users WHERE role='farmer' ORDER BY created_at DESC"
            )
            rows = cur.fetchall() or []
            for r in rows:
                r["id"] = int(r["id"])
                r["created_at"] = r["created_at"].isoformat()
            return jsonify(rows)
        finally:
            conn.close()

    @app.get("/api/admin/requests")
    def admin_requests():
        _, err = _require_admin()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT r.id, r.subject, r.message, r.status, r.created_at,
                       u.id AS farmer_id, u.name AS farmer_name, u.email AS farmer_email
                FROM requests r
                JOIN users u ON u.id = r.farmer_id
                WHERE r.status='open'
                ORDER BY r.created_at DESC, r.id DESC
                """
            )
            rows = cur.fetchall() or []
            for r in rows:
                r["id"] = int(r["id"])
                r["farmer_id"] = int(r["farmer_id"])
                r["created_at"] = r["created_at"].isoformat()
            return jsonify(rows)
        finally:
            conn.close()

    @app.post("/api/admin/requests/<int:request_id>/done")
    def admin_mark_request_done(request_id: int):
        _, err = _require_admin()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("UPDATE requests SET status='approved' WHERE id=%s", (request_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "request not found"}), 404
            return jsonify({"ok": True})
        finally:
            conn.close()

    @app.post("/api/admin/tasks")
    def admin_assign_task():
        _, err = _require_admin()
        if err:
            return err
        data = request.get_json(silent=True) or {}
        farmer_id = data.get("farmer_id")
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        if not farmer_id or not title:
            return jsonify({"error": "farmer_id and title are required"}), 400
        try:
            farmer_id_int = int(farmer_id)
        except Exception:
            return jsonify({"error": "farmer_id must be an integer"}), 400

        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id FROM users WHERE id=%s AND role='farmer'", (farmer_id_int,))
            if not cur.fetchone():
                return jsonify({"error": "farmer not found"}), 404
            cur.execute(
                "INSERT INTO tasks (farmer_id, title, description) VALUES (%s, %s, %s)",
                (farmer_id_int, title, description or None),
            )
            conn.commit()
            return jsonify({"ok": True, "id": int(cur.lastrowid)}), 201
        finally:
            conn.close()

    @app.get("/api/admin/farm-status")
    def admin_farm_status():
        _, err = _require_admin()
        if err:
            return err
        conn = get_db()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """
                SELECT u.id AS farmer_id, u.name AS farmer_name, u.email AS farmer_email,
                       fs.health, fs.crop_type, fs.moisture_percent, fs.updated_at
                FROM users u
                LEFT JOIN farm_status fs ON fs.farmer_id = u.id
                WHERE u.role='farmer'
                ORDER BY u.created_at DESC
                """
            )
            rows = cur.fetchall() or []
            for r in rows:
                r["farmer_id"] = int(r["farmer_id"])
                r["moisture_percent"] = int(r["moisture_percent"]) if r["moisture_percent"] is not None else None
                r["updated_at"] = r["updated_at"].isoformat() if r["updated_at"] else None
            return jsonify(rows)
        finally:
            conn.close()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
