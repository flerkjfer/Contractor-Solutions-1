import unittest
import sqlite3
import os
DB = "test_project.db"

def init_test_db():
    """Initialize the test database with all required tables"""
    conn = sqlite3.connect(DB)
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
        earnings REAL DEFAULT 0,
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
        client_approval TEXT CHECK(client_approval IN ('Pending','Approved','Denied')) DEFAULT 'Pending',
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

    conn.commit()
    conn.close()

class TestCRUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Initialize the database once before all tests"""
        init_test_db()

    def setUp(self):
        self.conn = sqlite3.connect(DB)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

        self.cur.execute("DELETE FROM User")
        self.cur.execute("DELETE FROM Client")
        self.cur.execute("DELETE FROM Contractor")
        self.cur.execute("DELETE FROM Company")
        self.cur.execute("DELETE FROM Job_Request")
        self.cur.execute("DELETE FROM Review")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    # create job request
    def test_create_job_request(self):
        #creates client
        self.cur.execute("INSERT INTO User(username, password, role) VALUES ('client1', 'password', 'client')")
        user_id = self.cur.lastrowid
        self.cur.execute("INSERT INTO Client (userID, firstName, lastName) VALUES (?, 'A', 'B')", (user_id,))
        client_id = self.cur.lastrowid

        #creates job request
        self.cur.execute("""INSERT INTO Job_Request (clientID, service, status, date_posted) VALUES (?, 'Plumbing', 'Pending', DATE('now'))""", (client_id,))
        self.conn.commit()

        self.cur.execute("SELECT * FROM Job_Request WHERE clientID=?", (client_id,))
        job = self.cur.fetchone()
        self.assertIsNotNone(job)
        self.assertEqual(job["service"], "Plumbing")

    # edit job request
    def test_edit_job_request(self):
        self.cur.execute("INSERT INTO Job_Request (clientID, service, status, date_posted) VALUES (1, 'Cleaning', 'Pending', DATE('now'))")
        job_id = self.cur.lastrowid

        self.cur.execute("UPDATE Job_Request SET service=? WHERE jobID=?", ("Painting", job_id))
        self.conn.commit()

        self.cur.execute("SELECT service FROM Job_Request WHERE jobID=?", (job_id,))
        job = self.cur.fetchone()
        self.assertEqual(job["service"], "Painting")

    # delete job request
    def test_delete_job_request(self):
        self.cur.execute("INSERT INTO Job_Request (clientID, service, status, date_posted) VALUES (1, 'Repair', 'Pending', DATE('now'))")
        job_id = self.cur.lastrowid
        self.conn.commit()

        self.cur.execute("DELETE FROM Job_Request WHERE jobID=?", (job_id,))
        self.conn.commit()

        self.cur.execute("SELECT * FROM Job_Request WHERE jobID=?", (job_id,))
        job = self.cur.fetchone()
        self.assertIsNone(job)

    # edit client profile
    def test_edit_client_profile(self):
        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('client2', 'password', 'client')")
        uid = self.cur.lastrowid
        self.cur.execute("INSERT INTO Client (userID, firstName, lastName, city) VALUES (?, 'Second', 'Name', 'City1')", (uid,))
        self.conn.commit()

        self.cur.execute("UPDATE Client SET firstName=?, city=? WHERE userID=?", ("Name2", "City2", uid))
        self.conn.commit()

        self.cur.execute("SELECT * FROM Client WHERE userID=?", (uid,))
        row = self.cur.fetchone()
        self.assertEqual(row["firstName"], "Name2")
        self.assertEqual(row["city"], "City2")    

    # edit contractor profile
    def test_edit_contractor_profile(self):
        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('contractor1', 'password', 'contractor')")
        uid = self.cur.lastrowid
        self.cur.execute("INSERT INTO Contractor (userID, firstName, lastName, service, city) VALUES (?, 'Contractor', 'Name', 'Plumbing', 'City1')", (uid,))
        self.conn.commit()

        self.cur.execute("UPDATE Contractor SET service=?, city=? WHERE userID=?", ("Electrician", "City2", uid))
        self.conn.commit()

        self.cur.execute("SELECT * FROM Contractor WHERE userID=?", (uid,))
        row = self.cur.fetchone()

        self.assertEqual(row["service"], "Electrician")
        self.assertEqual(row["city"], "City2")

    # contractor claims job
    def test_contractor_claim_job(self):
        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('contractor2', 'password', 'contractor')")
        uid = self.cur.lastrowid
        self.cur.execute("INSERT INTO Contractor (userID, firstName, lastName) VALUES (?, 'FirstC', 'CLast')", (uid,))
        contractor_id = self.cur.lastrowid

        self.cur.execute("INSERT INTO Job_Request (clientID, service, status, date_posted) VALUES (1, 'Painting', 'Pending', DATE('now'))")
        job_id = self.cur.lastrowid

        self.cur.execute("UPDATE Job_Request SET contractorID=?, status='In Progress' WHERE jobID=?", (contractor_id, job_id))
        self.conn.commit()

        self.cur.execute("SELECT * FROM Job_Request WHERE jobID=?", (job_id,))
        job = self.cur.fetchone()
        self.assertEqual(job["contractorID"], contractor_id)
        self.assertEqual(job["status"], "In Progress")

    #recalculate contractor rating by averaging all ratings
    def test_contractor_rating_recalculation(self):
        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('contractor3', 'password', 'contractor')")
        uid = self.cur.lastrowid
        self.cur.execute("INSERT INTO Contractor (userID, firstName, lastName, rating, earnings) VALUES (?, 'SecondC', 'CLast', 5.0, 0)", (uid,))
        contractor_id = self.cur.lastrowid

        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('client5', 'password', 'client')")
        uid2 = self.cur.lastrowid
        self.cur.execute("INSERT INTO Client(userID, firstName, lastName) VALUES (?, 'Client4', 'Last4')", (uid2,))
        client_id = self.cur.lastrowid

        self.cur.execute("INSERT INTO Job_Request (clientID, service, status, date_posted) VALUES (?, 'Test', 'Pending', DATE('now'))", (client_id,))
        job_id = self.cur.lastrowid

        ratings = [5, 3, 4]
        for r in ratings:
            self.cur.execute("""INSERT INTO Review (jobID, clientID, contractorID, rating, comment, date) VALUES (?, ?, ?, ?, 'Test', DATE('now'))""", (job_id, client_id, contractor_id, r))

        self.cur.execute("SELECT AVG(rating) AS avg_rating FROM Review WHERE contractorID=?", (contractor_id,))
        avg_rating = self.cur.fetchone()["avg_rating"]

        self.cur.execute("UPDATE Contractor SET rating=? WHERE contractorID=?", (avg_rating, contractor_id,))
        self.conn.commit()

        self.cur.execute("SELECT rating FROM Contractor WHERE contractorID=?", (contractor_id, ))
        updated = self.cur.fetchone()["rating"]

        self.assertAlmostEqual(updated, 4.0, places=2)

    # after contractor completes job gets review and rating
    def test_contractor_completes_job(self):
        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('contractor5', 'password', 'contractor')")
        uid = self.cur.lastrowid
        self.cur.execute("INSERT INTO Contractor (userID, firstName, lastName, rating, earnings) VALUES (?, 'SecondC', 'CLast', 5.0, 0)", (uid,))
        contractor_id = self.cur.lastrowid

        self.cur.execute("INSERT INTO User (username, password, role) VALUES ('client8', 'password', 'client')")
        uid2 = self.cur.lastrowid
        self.cur.execute("INSERT INTO Client(userID, firstName, lastName) VALUES (?, 'Client8', 'Last4')", (uid2,))
        client_id = self.cur.lastrowid

        self.cur.execute("""INSERT INTO Job_Request (clientID, contractorID, service, status, date_posted) VALUES (?, ?, 'Plumbing', 'In Progress', DATE('now'))""", (client_id, contractor_id))
        job_id = self.cur.lastrowid

        self.cur.execute("INSERT INTO Review (jobID, clientID, contractorID, rating, comment, date) VALUES (?, ?, ?, 4, 'Good', DATE('now'))", (job_id, client_id, contractor_id))
        self.cur.execute("SELECT AVG(rating) AS avg_rating FROM Review WHERE contractorID=?", (contractor_id,))
        avg_rating = self.cur.fetchone()["avg_rating"]
        self.cur.execute("UPDATE Contractor SET rating=? WHERE contractorID=?", (avg_rating, contractor_id,))
        self.cur.execute("UPDATE Contractor SET earnings = earnings + 100 WHERE contractorID=?", (contractor_id,))
        self.cur.execute("UPDATE Job_Request SET status='Completed' WHERE jobID=?", (job_id,))
        self.conn.commit()

        self.cur.execute("SELECT * FROM Contractor WHERE contractorID=?", (contractor_id,))
        contractor = self.cur.fetchone()
        self.assertEqual(contractor["earnings"], 100)
        self.assertAlmostEqual(contractor["rating"], 4.0, places=2)

        self.cur.execute("SELECT status FROM Job_Request WHERE jobID=?", (job_id,))
        job = self.cur.fetchone()
        self.assertEqual(job["status"], "Completed")

if __name__ == "__main__":
    unittest.main()