from flask import Flask, render_template, request, redirect, session
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecret"

DB_FILE = "project.db"

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        # Users table
        cur.execute("""
        CREATE TABLE User (
            userID INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('contractor', 'client'))
        )""")
        # Company table
        cur.execute("""
        CREATE TABLE Company (
            companyID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            serviceType TEXT,
            location TEXT
        )""")
        # Contractor table
        cur.execute("""
        CREATE TABLE Contractor (
            contractorID INTEGER PRIMARY KEY AUTOINCREMENT,
            fullName TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            companyID INTEGER,
            FOREIGN KEY (companyID) REFERENCES Company(companyID)
        )""")
        conn.commit()
        conn.close()
        print("Database initialized.")

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- User utilities ---
def create_user(username, password, role):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)",
                (username, password, role))
    conn.commit()
    conn.close()

# --- Routes ---
@app.route("/")
def index():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM User WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()
        if user:
            session["user_id"] = user["userID"]
            session["role"] = user["role"]
            return redirect("/companies")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/companies")
def list_companies():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    return render_template("companies.html", companies=companies, role=session["role"])

@app.route("/companies/add", methods=["POST"])
def add_company():
    if session.get("role") != "client":
        return "Not allowed"
    name = request.form["name"]
    serviceType = request.form["serviceType"]
    location = request.form["location"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO Company (name, serviceType, location) VALUES (?, ?, ?)",
                (name, serviceType, location))
    conn.commit()
    return redirect("/companies")

@app.route("/companies/delete/<int:company_id>")
def delete_company(company_id):
    if session.get("role") != "client":
        return "Not allowed"
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Company WHERE companyID=?", (company_id,))
    conn.commit()
    return redirect("/companies")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
