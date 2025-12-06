from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "secret123"  # replace later if needed

DB = "database.db"

# ---------- DB SETUP ----------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Users
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Contractors example table
    c.execute("""
    CREATE TABLE IF NOT EXISTS contractors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    conn.commit()
    conn.close()

# ---------- CREATE USER HELPER ----------
def create_user(username, password):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
    conn.commit()
    conn.close()
    print(f"Created user {username}")

# ---------- ROUTES ----------

@app.route("/")
def home():
    if "user_id" in session:
        return "Logged in! Go to /contractors"
    return "Not logged in. Go to /login"

@app.route("/login", methods=["GET", "POST"])
def login():
    form = """
    <h2>Login</h2>
    <form method='POST'>
      Username: <input name='username'><br>
      Password: <input type='password' name='password'><br>
      <button type='submit'>Login</button>
    </form>
    """
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password=?", (u, p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            return redirect("/contractors")
        else:
            return form + "<p style='color:red;'>Invalid credentials</p>"

    return form

@app.route("/contractors")
def contractors():
    if "user_id" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    rows = c.execute("SELECT id, name FROM contractors").fetchall()
    conn.close()

    html = "<h2>Contractors</h2><ul>"
    for r in rows:
        html += f"<li>{r[1]} (id {r[0]})</li>"
    html += "</ul>"

    return html

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
