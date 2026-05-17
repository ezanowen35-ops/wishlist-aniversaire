from flask import Flask, jsonify, session, request, make_response, redirect
import os, sqlite3
from datetime import datetime

app = Flask(__name__, static_folder="static")
app.secret_key = "wishlist_2026_merged"

BIRTHDAY = datetime(2026, 5, 28, 22, 0, 0)

GIFTS = [
    {"id":1,  "name":"Bouquet Special",       "emoji":"💐", "desc":"Fleurs fraiches, makeup, Polaroid, skin care, air care"},
    {"id":2,  "name":"Parfum Rose d Emotion",  "emoji":"🌹", "desc":"Rose d emotion - Mydoria, grossiste parfum TikTok"},
    {"id":3,  "name":"Panier Shein",           "emoji":"🛍", "desc":"Validation de ton panier Shein complet"},
    {"id":4,  "name":"Paire de Chaussures",    "emoji":"👠", "desc":"Pointure 39 - surprise stylee"},
    {"id":5,  "name":"Vetements Taille L",     "emoji":"👗", "desc":"Personnalises ou non, selon tes gouts"},
    {"id":6,  "name":"Bijoux Dores",           "emoji":"✨",  "desc":"Personnalises ou non - preference doree"},
    {"id":7,  "name":"Perruque",               "emoji":"💇", "desc":"La perruque de tes reves"},
    {"id":8,  "name":"AirPods Pro",            "emoji":"🎧", "desc":"AirPods Pro 2 ou AirPods Pro 3"},
    {"id":9,  "name":"iPad",                   "emoji":"📱", "desc":"L iPad pour ta creativite"},
    {"id":10, "name":"Dark Romance",           "emoji":"🖤", "desc":"Livres Dark Romance - collection choisie"},
    {"id":11, "name":"Skin et Hair Care",      "emoji":"🧴", "desc":"Produits coreens de preference + hair care"},
    {"id":12, "name":"Body Care",              "emoji":"🛁", "desc":"Produits luxueux pour le corps"},
    {"id":13, "name":"Coffrets Parfum",        "emoji":"🎁", "desc":"Coffrets de parfum elegants"},
    {"id":14, "name":"Maillot du Barca",       "emoji":"⚽",   "desc":"Le maillot officiel FC Barcelona"},
    {"id":15, "name":"Kit Makeup Complet",     "emoji":"💄", "desc":"Kit ou trousse a makeup avec du makeup"},
]

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras
    print("Mode: PostgreSQL")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wishlist.db")
    print("Mode: SQLite local")

def get_db():
    if USE_PG:
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        c = sqlite3.connect(DB_PATH)
        c.row_factory = sqlite3.Row
        return c

def db_exec(conn, sql, params=()):
    if USE_PG:
        sql = sql.replace("?", "%s")
    cur = conn.cursor() if USE_PG else None
    if USE_PG:
        cur.execute(sql, params)
    else:
        cur = conn.execute(sql, params)
    return cur

def rows_to_list(cur):
    rows = cur.fetchall()
    return [dict(r) for r in rows]

def row_one(cur):
    r = cur.fetchone()
    return dict(r) if r else None

def init_db():
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS visitors (
            id SERIAL PRIMARY KEY, nom TEXT NOT NULL, prenom TEXT NOT NULL, UNIQUE(nom,prenom))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS selections (
            id SERIAL PRIMARY KEY, visitor_id INTEGER NOT NULL, gift_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(visitor_id,gift_id))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY, gift_id INTEGER NOT NULL, gift_name TEXT NOT NULL,
            quantity INTEGER NOT NULL, seen INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()
        cur.close()
    else:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS visitors (id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL, prenom TEXT NOT NULL, UNIQUE(nom,prenom));
            CREATE TABLE IF NOT EXISTS selections (id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id INTEGER NOT NULL, gift_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(visitor_id,gift_id));
            CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT,
                gift_id INTEGER NOT NULL, gift_name TEXT NOT NULL, quantity INTEGER NOT NULL,
                seen INTEGER DEFAULT 0, created_at DATETIME DEFAULT CURRENT_TIMESTAMP);
        """)
        conn.commit()
    conn.close()

init_db()

def nocache(r):
    r.headers["Cache-Control"] = "no-store,no-cache,must-revalidate,max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

def serve_html(filename):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", filename)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    r = make_response(content)
    r.headers["Content-Type"] = "text/html; charset=utf-8"
    return nocache(r)

# ── ANNIVERSAIREUSE ──

@app.route("/")
def birthday():
    return serve_html("birthday.html")

@app.route("/api/countdown")
def countdown():
    diff = BIRTHDAY - datetime.now()
    s = int(diff.total_seconds())
    if s <= 0:
        return jsonify(done=True)
    return jsonify(done=False, d=s//86400, h=(s%86400)//3600, m=(s%3600)//60, s=s%60)

@app.route("/api/notifications")
def notifications():
    conn = get_db()
    cur = db_exec(conn, "SELECT * FROM notifications WHERE seen=0 ORDER BY created_at DESC")
    rows = rows_to_list(cur)
    conn.close()
    for r in rows:
        if hasattr(r.get("created_at"), "strftime"):
            r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(rows)

@app.route("/api/mark_read", methods=["POST"])
def mark_read():
    conn = get_db()
    db_exec(conn, "UPDATE notifications SET seen=1")
    conn.commit()
    conn.close()
    return jsonify(ok=True)

@app.route("/api/messages")
def messages():
    conn = get_db()
    cur = db_exec(conn, "SELECT gift_name, quantity, created_at FROM notifications ORDER BY created_at DESC LIMIT 50")
    rows = rows_to_list(cur)
    conn.close()
    for r in rows:
        if hasattr(r.get("created_at"), "strftime"):
            r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
    return jsonify(rows)

@app.route("/api/reveal")
def reveal():
    if datetime.now() < BIRTHDAY:
        return jsonify(locked=True)
    conn = get_db()
    cur = db_exec(conn, "SELECT gift_id, SUM(quantity) as total FROM selections GROUP BY gift_id")
    rows = rows_to_list(cur)
    conn.close()
    totals = {r["gift_id"]: r["total"] for r in rows}
    return jsonify(locked=False, gifts=[dict(g, total=totals.get(g["id"], 0)) for g in GIFTS])

# ── VISITEURS ──

@app.route("/invites")
def invites():
    return serve_html("visitor.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    nom = (data.get("nom") or "").strip()
    prenom = (data.get("prenom") or "").strip()
    if not nom or not prenom:
        return jsonify(ok=False, error="Champs requis"), 400
    conn = get_db()
    cur = db_exec(conn, "SELECT id FROM visitors WHERE nom=? AND prenom=?", (nom, prenom))
    row = row_one(cur)
    if row:
        vid = row["id"]
    else:
        if USE_PG:
            cur = db_exec(conn, "INSERT INTO visitors(nom,prenom) VALUES(?,?) RETURNING id", (nom, prenom))
            vid = row_one(cur)["id"]
        else:
            cur = db_exec(conn, "INSERT INTO visitors(nom,prenom) VALUES(?,?)", (nom, prenom))
            vid = cur.lastrowid
        conn.commit()
    conn.close()
    session["vid"] = vid
    session["nom"] = nom
    session["prenom"] = prenom
    return jsonify(ok=True)

@app.route("/api/my_selections")
def my_selections():
    if not session.get("vid"):
        return jsonify({})
    conn = get_db()
    cur = db_exec(conn, "SELECT gift_id, quantity FROM selections WHERE visitor_id=?", (session["vid"],))
    rows = rows_to_list(cur)
    conn.close()
    return jsonify({str(r["gift_id"]): r["quantity"] for r in rows})

@app.route("/api/select", methods=["POST"])
def select():
    if not session.get("vid"):
        return jsonify(ok=False, error="Non connecte"), 401
    data = request.get_json(force=True)
    gift_id = int(data.get("gift_id", 0))
    quantity = max(1, min(20, int(data.get("quantity", 1))))
    gift = next((g for g in GIFTS if g["id"] == gift_id), None)
    if not gift:
        return jsonify(ok=False, error="Cadeau inconnu"), 404
    conn = get_db()
    db_exec(conn, """INSERT INTO selections(visitor_id,gift_id,quantity) VALUES(?,?,?)
        ON CONFLICT(visitor_id,gift_id) DO UPDATE SET quantity=EXCLUDED.quantity""",
        (session["vid"], gift_id, quantity))
    db_exec(conn, "INSERT INTO notifications(gift_id,gift_name,quantity) VALUES(?,?,?)",
        (gift_id, gift["name"], quantity))
    conn.commit()
    conn.close()
    return jsonify(ok=True, gift_name=gift["name"], quantity=quantity)

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify(ok=True)

@app.route("/static/images/<path:name>")
def img(name):
    from flask import send_from_directory
    return send_from_directory("static/images", name)

if __name__ == "__main__":
    print("")
    print("=" * 50)
    print("  WISHLIST ANNIVERSAIRE")
    print("=" * 50)
    print("  Anniversaireuse -> http://localhost:5000/")
    print("  Invites         -> http://localhost:5000/invites")
    print("=" * 50)
    app.run(port=5000, debug=False)