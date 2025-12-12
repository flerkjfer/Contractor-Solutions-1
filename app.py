from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "supersecret"
DB_FILE = "project.db"

# -------------------------------
# Database Initialization
# -------------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS User (
        userID INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('contractor', 'client'))
    );""")

    # Companies
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Company (
        companyID INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        serviceType TEXT,
        location TEXT
    );""")

    # Contractors
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
    );""")

    # Clients
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
    );""")

    # Job Requests
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
    );""")

    # Transactions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Transactions (
        transactionID INTEGER PRIMARY KEY AUTOINCREMENT,
        jobID INTEGER NOT NULL,
        clientID INTEGER NOT NULL,
        contractorID INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT CHECK(method IN ('Credit Card','Debit Card','PayPal','Cash','Check')) NOT NULL,
        date DATE NOT NULL,
        FOREIGN KEY(jobID) REFERENCES Job_Request(jobID),
        FOREIGN KEY(clientID) REFERENCES Client(clientID),
        FOREIGN KEY(contractorID) REFERENCES Contractor(contractorID)
    );""")

    # Reviews table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Review (
        reviewID INTEGER PRIMARY KEY AUTOINCREMENT,
        jobID INTEGER NOT NULL,
        clientID INTEGER NOT NULL,
        contractorID INTEGER NOT NULL,
        rating INTEGER CHECK(rating BETWEEN 1 AND 5),
        comment TEXT,
        date DATE NOT NULL,
        FOREIGN KEY(jobID) REFERENCES Job_Request(jobID),
        FOREIGN KEY(clientID) REFERENCES Client(clientID),
        FOREIGN KEY(contractorID) REFERENCES Contractor(contractorID)
    );""")

    # Contractor claim requests table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Contractor_Claim_Request (
        requestID INTEGER PRIMARY KEY AUTOINCREMENT,
        jobID INTEGER NOT NULL,
        contractorID INTEGER NOT NULL,
        status TEXT CHECK(status IN ('Pending', 'Accepted', 'Declined')) DEFAULT 'Pending',
        date_requested DATE NOT NULL,
        FOREIGN KEY(jobID) REFERENCES Job_Request(jobID),
        FOREIGN KEY(contractorID) REFERENCES Contractor(contractorID)
    );
    """)



    # Add earnings column to Contractor if it doesn't exist
    try:
        cur.execute("ALTER TABLE Contractor ADD COLUMN earnings REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    # Add client_approval column to Job_Request if it doesn't exist
    try:
        cur.execute("""
        ALTER TABLE Job_Request
        ADD COLUMN client_approval TEXT CHECK(client_approval IN ('Pending','Approved','Denied')) DEFAULT 'Pending'
        """)
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_client_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT clientID FROM Client WHERE userID=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["clientID"] if row else None

def get_contractor_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT contractorID FROM Contractor WHERE userID=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["contractorID"] if row else None


# -------------------------------
# User Utilities
# -------------------------------
def create_user(username, password, role):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO User (username, password, role) VALUES (?, ?, ?)",
                (username, password, role))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return user_id

# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/dashboard")
    return redirect("/login")

# ----- Auth -----
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

@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/forgot")
def forgotPasswordPage():
    return render_template("fp.html")



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

# ----- Dashboard -----
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

    # Client profile
    cur.execute("SELECT * FROM Client WHERE userID=?", (user_id,))
    profile = cur.fetchone()

    # Companies
    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()

    # Pending contractor claim requests for this client's jobs
    cur.execute("""
        SELECT jc.*, c.firstName || ' ' || c.lastName AS contractorName, jr.service
        FROM Contractor_Claim_Request jc
        JOIN Contractor c ON jc.contractorID = c.contractorID
        JOIN Job_Request jr ON jc.jobID = jr.jobID
        WHERE jr.clientID=? AND jc.status='Pending'
        ORDER BY jc.date_requested DESC
    """, (profile["clientID"],))
    pending_claims = cur.fetchall()

    conn.close()
    return render_template(
        "dashboard_client.html",
        profile=profile,
        companies=companies,
        contractor_requests=pending_claims
    )

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

# ----- Profile Edit -----
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

# ----- Companies -----
@app.route("/companies")
def companies():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()

    role = session.get("role")  # 'client' or 'contractor'

    # contractors get management page
    if role == "contractor":
        return render_template("companies_manage.html", companies=companies)

    # clients get read-only view
    return render_template("companies_view.html", companies=companies)

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
    if session.get("role") != "contractor":
        return "Forbidden", 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM Company WHERE companyID=?", (company_id,))
    conn.commit()

    return redirect("/companies")

@app.post("/companies/create")
def create_company():
    if session.get("role") != "contractor":
        return "Forbidden", 403

    name = request.form["name"]
    service = request.form["serviceType"]
    location = request.form["location"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO Company (name, serviceType, location)
        VALUES (?, ?, ?)
    """, (name, service, location))

    conn.commit()
    return redirect("/companies")

@app.route("/companies/<int:company_id>/jobs")
def view_company_jobs(company_id):
    conn = sqlite3.connect('project.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT jobID, service, status
        FROM Job_Request
        WHERE companyID = ?
    """, (company_id,))
    jobs = cursor.fetchall()

    conn.close()
    return render_template("company_jobs.html", jobs=jobs, company_id=company_id)

# ----- Contractors -----
@app.route("/contractors")
def list_contractors():
    if "user_id" not in session:
        return redirect("/login")
    conn = get_db()
    cur = conn.cursor()

    # Fetch all contractors with average rating
    cur.execute("""
        SELECT ctr.*, 
               IFNULL(AVG(r.rating), 0) AS avg_rating
        FROM Contractor ctr
        LEFT JOIN Review r ON ctr.contractorID = r.contractorID
        GROUP BY ctr.contractorID
    """)
    contractors = cur.fetchall()

    # Fetch all reviews for all contractors
    contractor_reviews = {}
    cur.execute("""
        SELECT r.contractorID, r.comment, r.rating, c.firstName || ' ' || c.lastName AS clientName
        FROM Review r
        JOIN Client c ON r.clientID = c.clientID
    """)
    for row in cur.fetchall():
        contractor_reviews.setdefault(row["contractorID"], []).append({
            "comment": row["comment"],
            "rating": row["rating"],
            "clientName": row["clientName"]
        })

    conn.close()
    return render_template("contractors.html", contractors=contractors, contractor_reviews=contractor_reviews)

# -------------------------------
# Job Requests
# -------------------------------
@app.route("/jobrequests")
def view_jobrequests():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "client":
        return "Only clients can view their job requests", 403

    conn = get_db()
    cur = conn.cursor()
    # Get clientID
    cur.execute("SELECT clientID FROM Client WHERE userID=?", (session["user_id"],))
    client_row = cur.fetchone()
    if not client_row:
        return "Client profile not found", 400
    client_id = client_row["clientID"]

    # Only their own job requests
    cur.execute("""
        SELECT jr.*, c.name AS companyName
        FROM Job_Request jr
        LEFT JOIN Company c ON jr.companyID = c.companyID
        WHERE jr.clientID=?
        ORDER BY jr.date_posted DESC
    """, (client_id,))
    jobrequests = cur.fetchall()
    conn.close()
    return render_template("view_jobrequests.html", jobrequests=jobrequests, role="client")

@app.route("/jobrequests/new", methods=["GET", "POST"])
def create_jobrequest():
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "client":
        return "Only clients can create job requests", 403

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT clientID FROM Client WHERE userID=?", (session["user_id"],))
    client_row = cur.fetchone()
    if not client_row:
        return "Client profile not found", 400
    client_id = client_row["clientID"]

    if request.method == "POST":
        company_id = request.form.get("companyID") or None
        service = request.form["service"]
        cur.execute("""
            INSERT INTO Job_Request (clientID, companyID, service, status, date_posted)
            VALUES (?, ?, ?, 'Pending', DATE('now'))
        """, (client_id, company_id, service))
        conn.commit()
        conn.close()
        return redirect(url_for("view_jobrequests"))

    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    conn.close()
    return render_template("job_request_new.html", companies=companies)

@app.route("/jobrequests/edit/<int:job_id>", methods=["GET", "POST"])
def edit_jobrequest(job_id):
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "client":
        return "Only clients can edit job requests", 403

    conn = get_db()
    cur = conn.cursor()
    # Check ownership
    cur.execute("SELECT * FROM Job_Request WHERE jobID=?", (job_id,))
    job = cur.fetchone()
    if not job or job["clientID"] != get_client_id(session["user_id"]):
        return "Access denied", 403

    if request.method == "POST":
        service = request.form["service"]
        company_id = request.form.get("companyID") or None
        cur.execute("""
            UPDATE Job_Request SET service=?, companyID=? WHERE jobID=?
        """, (service, company_id, job_id))
        conn.commit()
        conn.close()
        return redirect(url_for("view_jobrequests"))

    cur.execute("SELECT * FROM Company")
    companies = cur.fetchall()
    conn.close()
    return render_template("edit_jobrequest.html", job=job, companies=companies)

@app.route("/jobrequests/delete/<int:job_id>")
def delete_jobrequest(job_id):
    if "user_id" not in session:
        return redirect("/login")
    if session.get("role") != "client":
        return "Only clients can delete job requests", 403

    conn = get_db()
    cur = conn.cursor()
    # Check ownership
    cur.execute("SELECT * FROM Job_Request WHERE jobID=?", (job_id,))
    job = cur.fetchone()
    if not job or job["clientID"] != get_client_id(session["user_id"]):
        return "Access denied", 403

    cur.execute("DELETE FROM Job_Request WHERE jobID=?", (job_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_jobrequests"))

# ----- Contractor updates job status -----
@app.route("/jobrequests/complete/<int:job_id>", methods=["GET", "POST"])
def complete_job(job_id):
    if session.get("role") != "client":
        return "Access denied", 403

    client_id = get_client_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Job_Request WHERE jobID=? AND clientID=?", (job_id, client_id))
    job = cur.fetchone()
    if not job or job["status"] != "In Progress":
        conn.close()
        return "Job not available", 400

    if request.method == "POST":
        rating = int(request.form["rating"])
        review_text = request.form.get("review")
        payment = min(float(request.form["payment"]), 100000)

        contractor_id = job["contractorID"]

        # Insert review
        cur.execute("""
            INSERT INTO Review (jobID, clientID, contractorID, rating, comment, date)
            VALUES (?, ?, ?, ?, ?, DATE('now'))
        """, (job_id, client_id, contractor_id, rating, review_text))

        # Update contractor earnings
        cur.execute("UPDATE Contractor SET earnings = earnings + ? WHERE contractorID=?", (payment, contractor_id))

        # Update job status
        cur.execute("UPDATE Job_Request SET status='Completed' WHERE jobID=?", (job_id,))

        # Update contractor average rating
        cur.execute("SELECT AVG(rating) as avg_rating FROM Review WHERE contractorID=?", (contractor_id,))
        avg = cur.fetchone()["avg_rating"]
        cur.execute("UPDATE Contractor SET rating=? WHERE contractorID=?", (avg, contractor_id))

        conn.commit()
        conn.close()
        return redirect(url_for("client_jobs"))

    conn.close()
    return render_template("complete_job.html", job=job)

# -------------------------------
# Client approves or denies job completion
# -------------------------------
@app.route("/jobrequests/approval/<int:job_id>", methods=["GET", "POST"])
def client_approval(job_id):
    if "user_id" not in session or session.get("role") != "client":
        return redirect("/login")

    client_id = get_client_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Job_Request WHERE jobID=? AND clientID=?", (job_id, client_id))
    job = cur.fetchone()
    if not job:
        conn.close()
        return "Job not found", 404

    if request.method == "POST":
        decision = request.form.get("decision")
        if decision not in ("Approved","Denied"):
            conn.close()
            return "Invalid decision", 400
        cur.execute("UPDATE Job_Request SET client_approval=? WHERE jobID=?", (decision, job_id))
        conn.commit()
        conn.close()
        if decision == "Approved":
            return redirect(f"/jobrequests/payment/{job_id}")
        return redirect("/jobrequests")
    
    conn.close()
    return render_template("client_approval.html", job=job)

# -------------------------------
# Client pays contractor
# -------------------------------
@app.route("/jobrequests/payment/<int:job_id>", methods=["GET", "POST"])
def client_payment(job_id):
    if "user_id" not in session or session.get("role") != "client":
        return redirect("/login")

    client_id = get_client_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Job_Request WHERE jobID=? AND clientID=?", (job_id, client_id))
    job = cur.fetchone()
    if not job or job["client_approval"] != "Approved":
        conn.close()
        return "Payment not allowed", 403

    contractor_id = job["contractorID"]
    if not contractor_id:
        conn.close()
        return "No contractor assigned", 400

    if request.method == "POST":
        amount = float(request.form["amount"])
        method = request.form["method"]
        cur.execute("""
            INSERT INTO Transactions (jobID, clientID, contractorID, amount, method, date)
            VALUES (?, ?, ?, ?, ?, DATE('now'))
        """, (job_id, client_id, contractor_id, amount, method))
        # Update contractor earnings
        cur.execute("UPDATE Contractor SET earnings = earnings + ? WHERE contractorID=?", (amount, contractor_id))
        conn.commit()
        conn.close()
        return redirect(f"/jobrequests/review/{job_id}")

    conn.close()
    return render_template("client_payment.html", job=job)

# -------------------------------
# Client leaves a review
# -------------------------------
@app.route("/jobrequests/review/<int:job_id>", methods=["GET", "POST"])
def client_review(job_id):
    if "user_id" not in session or session.get("role") != "client":
        return redirect("/login")

    client_id = get_client_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Job_Request WHERE jobID=? AND clientID=?", (job_id, client_id))
    job = cur.fetchone()
    if not job:
        conn.close()
        return "Job not found", 404

    contractor_id = job["contractorID"]
    if request.method == "POST":
        rating = int(request.form["rating"])
        comment = request.form.get("comment")
        cur.execute("""
            INSERT INTO Review (jobID, clientID, contractorID, rating, comment, date)
            VALUES (?, ?, ?, ?, ?, DATE('now'))
        """, (job_id, client_id, contractor_id, rating, comment))
        # Update contractor average rating
        cur.execute("""
            SELECT AVG(rating) as avg_rating FROM Review WHERE contractorID=?
        """, (contractor_id,))
        avg = cur.fetchone()["avg_rating"]
        cur.execute("UPDATE Contractor SET rating=? WHERE contractorID=?", (avg, contractor_id))
        conn.commit()
        conn.close()
        return redirect("/dashboard/client")

    conn.close()
    return render_template("client_review.html", job=job)

# Contractor sees open jobs and their claimed jobs
@app.route("/dashboard/contractor/jobs")
def contractor_jobs():
    if session.get("role") != "contractor":
        return "Access denied", 403

    contractor_id = get_contractor_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()
    
    # Open jobs (not yet claimed)
    cur.execute("""
        SELECT jr.*, c.name AS companyName, cli.firstName || ' ' || cli.lastName AS clientName
        FROM Job_Request jr
        LEFT JOIN Company c ON jr.companyID = c.companyID
        LEFT JOIN Client cli ON jr.clientID = cli.clientID
        WHERE jr.contractorID IS NULL
        ORDER BY jr.date_posted DESC
    """)
    open_jobs = cur.fetchall()


    # My claimed jobs
    cur.execute("""
        SELECT jr.*, c.name AS companyName, cli.firstName || ' ' || cli.lastName AS clientName
        FROM Job_Request jr
        LEFT JOIN Company c ON jr.companyID = c.companyID
        LEFT JOIN Client cli ON jr.clientID = cli.clientID
        WHERE jr.contractorID=?
        ORDER BY jr.date_posted DESC
    """, (contractor_id,))
    my_jobs = cur.fetchall()
    
    conn.close()
    return render_template("contractor_jobs.html", open_jobs=open_jobs, my_jobs=my_jobs)

# Contractor claims a job
@app.route("/jobrequests/claim/<int:job_id>")
def claim_job(job_id):
    if session.get("role") != "contractor":
        return "Access denied", 403

    contractor_id = get_contractor_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()

    # Only allow claiming pending/unassigned jobs
    cur.execute("SELECT * FROM Job_Request WHERE jobID=? AND status='Pending'", (job_id,))
    job = cur.fetchone()
    if not job:
        conn.close()
        return "Job not available", 400

    # Assign contractor and set status to in progress
    cur.execute("UPDATE Job_Request SET contractorID=?, status='In Progress' WHERE jobID=?",
                (contractor_id, job_id))
    conn.commit()
    conn.close()
    return redirect(url_for("contractor_jobs"))

@app.route("/dashboard/client/jobs")
def client_jobs():
    if session.get("role") != "client":
        return "Access denied", 403
    
    client_id = get_client_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT jr.*, c.name AS companyName, ctr.firstName || ' ' || ctr.lastName AS contractorName
        FROM Job_Request jr
        LEFT JOIN Company c ON jr.companyID = c.companyID
        LEFT JOIN Contractor ctr ON jr.contractorID = ctr.contractorID
        WHERE jr.clientID=?
        ORDER BY jr.date_posted DESC
    """, (client_id,))
    jobs = cur.fetchall()
    conn.close()
    return render_template("client_jobs.html", jobs=jobs)

@app.route("/dashboard/contractor/ratings")
def contractor_ratings():
    if session.get("role") != "contractor":
        return "Access denied", 403

    contractor_id = get_contractor_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()

    # Contractor info
    cur.execute("SELECT * FROM Contractor WHERE contractorID=?", (contractor_id,))
    contractor = cur.fetchone()

    # Reviews
    cur.execute("SELECT r.*, c.firstName || ' ' || c.lastName AS clientName FROM Review r JOIN Client c ON r.clientID=c.clientID WHERE contractorID=?", (contractor_id,))
    reviews = cur.fetchall()
    conn.close()
    return render_template("contractor_ratings.html", contractor=contractor, reviews=reviews)

@app.route("/request_claim/<int:job_id>")
def request_claim(job_id):
    if session.get("role") != "contractor":
        return "Access denied", 403

    contractor_id = get_contractor_id(session["user_id"])
    conn = get_db()
    cur = conn.cursor()

    # Prevent duplicates
    cur.execute("""
        SELECT * FROM Contractor_Claim_Request
        WHERE jobID=? AND contractorID=?
    """, (job_id, contractor_id))
    existing = cur.fetchone()

    if existing:
        conn.close()
        return redirect("/dashboard/contractor/jobs")

    # Insert new claim request
    cur.execute("""
        INSERT INTO Contractor_Claim_Request (jobID, contractorID, status, date_requested)
        VALUES (?, ?, 'Pending', DATE('now'))
    """, (job_id, contractor_id))

    conn.commit()
    conn.close()

    return redirect("/dashboard/contractor/jobs")


@app.route("/approve_contractor/<int:job_id>/<int:contractor_id>")
def approve_contractor(job_id, contractor_id):
    if session.get("role") != "client":
        return "Access denied", 403

    conn = get_db()
    cur = conn.cursor()

    # Accept this contractor
    cur.execute("""
        UPDATE Contractor_Claim_Request
        SET status='Accepted'
        WHERE jobID=? AND contractorID=?
    """, (job_id, contractor_id))

    # Reject all others
    cur.execute("""
        UPDATE Contractor_Claim_Request
        SET status='Declined'
        WHERE jobID=? AND contractorID<>?
    """, (job_id, contractor_id))

    # Assign contractor to the job
    cur.execute("""
        UPDATE Job_Request
        SET contractorID=?, status='In Progress'
        WHERE jobID=?
    """, (contractor_id, job_id))

    conn.commit()
    conn.close()
    return redirect("/dashboard/client")

@app.route("/reject_contractor/<int:job_id>/<int:contractor_id>")
def reject_contractor(job_id, contractor_id):
    if session.get("role") != "client":
        return "Access denied", 403

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE Contractor_Claim_Request
        SET status='Declined'
        WHERE jobID=? AND contractorID=?
    """, (job_id, contractor_id))

    conn.commit()
    conn.close()
    return redirect("/dashboard/client")

@app.route("/contractor_profile/<int:contractor_id>")
def contractor_profile(contractor_id):
    conn = get_db()
    cur = conn.cursor()

    # Fetch contractor basic info
    cur.execute("""
        SELECT firstName, lastName, rating
        FROM Contractor
        WHERE contractorID=?
    """, (contractor_id,))
    contractor = cur.fetchone()

    # Fetch all reviews with client names
    cur.execute("""
        SELECT r.comment, r.rating, r.date, c.firstName || ' ' || c.lastName AS clientName
        FROM Review r
        JOIN Client c ON r.clientID = c.clientID
        WHERE r.contractorID=?
        ORDER BY r.date DESC
    """, (contractor_id,))
    reviews = cur.fetchall()

    conn.close()
    return render_template(
        "contractor_profile.html",
        contractor=contractor,
        reviews=reviews
    )




# -------------------------------
# Helper Functions
# -------------------------------
def get_client_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT clientID FROM Client WHERE userID=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["clientID"] if row else None

def get_contractor_id(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT contractorID FROM Contractor WHERE userID=?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["contractorID"] if row else None


# -------------------------------
# Run App
# -------------------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
