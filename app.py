from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "supersecret"

DB_FILE = "project.db"

def init_db():
    """Ensure all required tables exist."""
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS User (
        userID INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('contractor', 'client'))
    );
    """)

    # Company table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Company (
        companyID INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        serviceType TEXT,
        location TEXT
    );
    """)

    # Contractor table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Contractor (
        contractorID INTEGER PRIMARY KEY AUTOINCREMENT,
        userID INTEGER UNIQUE NOT NULL,
        companyID INTEGER,
        service TEXT,
        firstName TEXT NOT NULL,
        lastName TEXT NOT NULL,
        city TEXT,
        state CHAR(2),
        rating REAL,
        FOREIGN KEY(userID) REFERENCES User(userID),
        FOREIGN KEY(companyID) REFERENCES Company(companyID)
    );
    """)

    # Client table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Client (
        clientID INTEGER PRIMARY KEY AUTOINCREMENT,
        userID INTEGER UNIQUE NOT NULL,
        firstName TEXT NOT NULL,
        lastName TEXT NOT NULL,
        address TEXT,
        streetNumber TEXT,
        streetName TEXT,
        aptNumber TEXT,
        city TEXT,
        state CHAR(2),
        zip TEXT,
        FOREIGN KEY(userID) REFERENCES User(userID)
    );
    """)

    # Job_Request table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Job_Request (
        jobID INTEGER PRIMARY KEY AUTOINCREMENT,
        clientID INTEGER NOT NULL,
        contractorID INTEGER,
        companyID INTEGER,
        service TEXT,
        status TEXT CHECK(status IN ('Pending','In Progress','Completed','Cancelled')) DEFAULT 'Pending',
        date_posted DATE NOT NULL,
        date_fulfilled DATE,
        FOREIGN KEY(clientID) REFERENCES Client(clientID),
        FOREIGN KEY(contractorID) REFERENCES Contractor(contractorID),
        FOREIGN KEY(companyID) REFERENCES Company(companyID)
    );
    """)

    conn.commit()
    conn.close()
    print("init_db: ensured tables exist.")

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
    user_id = cur.lastrowid
    conn.close()
    return user_id

# --- Routes ---
@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/dashboard")
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
        conn.close()
        if user:
            session["user_id"] = user["userID"]
            session["role"] = user["role"]
            return redirect("/dashboard")
        return "Invalid credentials"
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        try:
            user_id = create_user(username, password, role)

            conn = get_db()
            cur = conn.cursor()
            if role == "client":
                cur.execute("""
                    INSERT INTO Client (userID, firstName, lastName)
                    VALUES (?, ?, ?)
                """, (user_id, "First", "Last"))
            else:
                cur.execute("""
                    INSERT INTO Contractor (userID, firstName, lastName, service)
                    VALUES (?, ?, ?, ?)
                """, (user_id, "First", "Last", "General"))
            conn.commit()
            conn.close()
            return redirect("/login")
        except Exception as e:
            return f"Registration failed: {e}"
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
def dashboard_redirect():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") == "client":
        return redirect("/dashboard/client")
    return redirect("/dashboard/contractor")

@app.route("/dashboard/client")
def client_dashboard():
    if session.get("role") != "client":
        return "Access denied", 403
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Client WHERE userID=?", (user_id,))
    profile = cur.fetchone()

    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    conn.close()
    return render_template("dashboard_client.html", profile=profile, companies=companies)

@app.route("/dashboard/contractor")
def contractor_dashboard():
    if session.get("role") != "contractor":
        return "Access denied", 403
    user_id = session["user_id"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Contractor WHERE userID=?", (user_id,))
    profile = cur.fetchone()

    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    conn.close()
    return render_template("dashboard_contractor.html", profile=profile, companies=companies)

# Profile edit
@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        return redirect("/login")
    user_id = session["user_id"]
    role = session["role"]
    conn = get_db()
    cur = conn.cursor()

    if request.method == "POST":
        if role == "client":
            cur.execute("""
                UPDATE Client SET
                    firstName=?, lastName=?, address=?, streetNumber=?, streetName=?,
                    aptNumber=?, city=?, state=?, zip=?
                WHERE userID=?
            """, (
                request.form.get("firstName"),
                request.form.get("lastName"),
                request.form.get("address"),
                request.form.get("streetNumber"),
                request.form.get("streetName"),
                request.form.get("aptNumber"),
                request.form.get("city"),
                request.form.get("state"),
                request.form.get("zip"),
                user_id
            ))
        else:
            cur.execute("""
                UPDATE Contractor SET
                    firstName=?, lastName=?, service=?, city=?, state=?, rating=?
                WHERE userID=?
            """, (
                request.form.get("firstName"),
                request.form.get("lastName"),
                request.form.get("service"),
                request.form.get("city"),
                request.form.get("state"),
                request.form.get("rating") or None,
                user_id
            ))
        conn.commit()
        conn.close()
        return redirect("/dashboard")

    if role == "client":
        cur.execute("SELECT * FROM Client WHERE userID=?", (user_id,))
        profile = cur.fetchone()
        conn.close()
        return render_template("profile_edit_client.html", profile=profile)
    else:
        cur.execute("SELECT * FROM Contractor WHERE userID=?", (user_id,))
        profile = cur.fetchone()
        conn.close()
        return render_template("profile_edit_contractor.html", profile=profile)

# Companies
@app.route("/companies")
def list_companies():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    conn.close()
    return render_template("companies.html", companies=companies, role=session["role"])

@app.route("/companies/add", methods=["POST"])
def add_company():
    if session.get("role") != "client":
        return "Not allowed", 403
    name = request.form["name"]
    serviceType = request.form["serviceType"]
    location = request.form["location"]
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO Company (name, serviceType, location) VALUES (?, ?, ?)",
                (name, serviceType, location))
    conn.commit()
    conn.close()
    return redirect("/companies")

@app.route("/companies/delete/<int:company_id>")
def delete_company(company_id):
    if session.get("role") != "client":
        return "Not allowed", 403
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Company WHERE companyID=?", (company_id,))
    conn.commit()
    conn.close()
    return redirect("/companies")

# Contractors list
@app.route("/contractors")
def list_contractors():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Contractor")
    contractors = cur.fetchall()
    conn.close()
    return render_template("contractors.html", contractors=contractors)

# --- Job Requests ---
@app.route("/jobrequests")
def view_jobrequests():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "client":
        return "Only clients can view their job requests", 403

    conn = get_db()
    cur = conn.cursor()

    # Get the clientID first
    cur.execute("SELECT clientID FROM Client WHERE userID=?", (session["user_id"],))
    client_row = cur.fetchone()
    if not client_row:
        return "Client profile not found", 400
    client_id = client_row["clientID"]

    cur.execute("""
        SELECT jr.*, c.name AS company_name
        FROM Job_Request jr
        LEFT JOIN Company c ON jr.companyID = c.companyID
        WHERE jr.clientID=?
        ORDER BY jr.date_posted DESC
    """, (client_id,))
    jobrequests = cur.fetchall()
    conn.close()
    return render_template("view_jobrequests.html", jobrequests=jobrequests)

@app.route("/jobrequests/new", methods=["GET", "POST"])
def create_jobrequest():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "client":
        return "Only clients can create job requests", 403

    conn = get_db()
    cur = conn.cursor()

    # Get clientID from session user_id
    cur.execute("SELECT clientID FROM Client WHERE userID=?", (session["user_id"],))
    client_row = cur.fetchone()
    if not client_row:
        return "Client profile not found", 400
    client_id = client_row["clientID"]

    if request.method == "POST":
        company_id = request.form["companyID"]
        service = request.form["service"]
        cur.execute("""
            INSERT INTO Job_Request (clientID, companyID, service, status, date_posted)
            VALUES (?, ?, ?, 'Pending', DATE('now'))
        """, (client_id, company_id, service))
        conn.commit()
        conn.close()
        return redirect(url_for("view_jobrequests"))

    # GET: show form
    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    conn.close()
    return render_template("job_request_new.html", companies=companies)

@app.route("/clients")
def view_all_clients():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Client")
    clients = cur.fetchall()
    conn.close()
    return render_template("view_clients.html", clients=clients)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
