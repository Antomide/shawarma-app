
import os
import sqlite3
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=None)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "shawarma.db")
WEBAPP_DIR = os.path.join(os.path.dirname(__file__), "..", "webapp")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            addr TEXT NOT NULL,
            hours TEXT NOT NULL,
            wait TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL,
            location_name TEXT NOT NULL,
            items_json TEXT NOT NULL,
            total INTEGER NOT NULL,
            telegram_user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    count = conn.execute("SELECT COUNT(*) as c FROM locations").fetchone()["c"]
    if count == 0:
        seed = [
            ("ТЦ Галерея", "ул. Ленина, 12", "10:00–22:00", "~10 мин", 55.7558, 37.6173),
            ("Площадь Победы", "пр. Мира, 5", "09:00–23:00", "~7 мин", 55.7298, 37.5996),
            ("Рынок Центральный", "ул. Садовая, 44", "08:00–21:00", "~5 мин", 55.7489, 37.6452),
        ]
        conn.executemany(
            "INSERT INTO locations (name, addr, hours, wait, lat, lng) VALUES (?, ?, ?, ?, ?, ?)",
            seed
        )
        conn.commit()
    conn.close()


@app.route("/api/locations", methods=["GET"])
def get_locations():
    conn = get_db()
    rows = conn.execute("SELECT * FROM locations ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/locations", methods=["POST"])
def add_location():
    data = request.get_json()
    required = ["name", "addr", "hours", "wait", "lat", "lng"]
    if not all(k in data for k in required):
        return jsonify({"error": "Не хватает полей"}), 400
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO locations (name, addr, hours, wait, lat, lng) VALUES (?, ?, ?, ?, ?, ?)",
        (data["name"], data["addr"], data["hours"], data["wait"], data["lat"], data["lng"])
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, **data}), 201


@app.route("/api/locations/<int:loc_id>", methods=["DELETE"])
def delete_location(loc_id):
    conn = get_db()
    conn.execute("DELETE FROM locations WHERE id = ?", (loc_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": loc_id})


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json()
    required = ["order_number", "location_name", "items", "total"]
    if not all(k in data for k in required):
        return jsonify({"error": "Не хватает полей"}), 400
    import json
    conn = get_db()
    conn.execute(
        "INSERT INTO orders (order_number, location_name, items_json, total, telegram_user_id) VALUES (?, ?, ?, ?, ?)",
        (data["order_number"], data["location_name"], json.dumps(data["items"], ensure_ascii=False),
         data["total"], data.get("telegram_user_id"))
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"}), 201


@app.route("/api/orders", methods=["GET"])
def get_orders():
    conn = get_db()
    rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/")
def serve_index():
    return send_from_directory(WEBAPP_DIR, "index.html")


@app.route("/admin")
@app.route("/admin.html")
def serve_admin():
    return send_from_directory(WEBAPP_DIR, "admin.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(WEBAPP_DIR, filename)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print("Сервер запущен на порту", port)
    app.run(host="0.0.0.0", port=port, debug=False)
