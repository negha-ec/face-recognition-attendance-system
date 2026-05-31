"""
Database Module
================
Run once to initialize:
    python3 database2.py
"""

import sqlite3
from datetime import date, datetime

DATABASE_FILE = "attendance.db"


def get_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            roll_no      INTEGER PRIMARY KEY,
            student_id   TEXT NOT NULL UNIQUE,
            student_name TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            subject   TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id   TEXT NOT NULL,
            student_id   TEXT NOT NULL,
            student_name TEXT NOT NULL,
            subject      TEXT NOT NULL,
            date         TEXT NOT NULL,
            time         TEXT NOT NULL,
            marked_by    TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")


# ── STUDENT FUNCTIONS ─────────────────────────────────────────────────────────

def seed_students():
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    conn.close()

    if count == 0:
        students = [
            (18, "PRN23EC018", "Midhila Raj"),
            (28, "PRN23EC087", "Nandana P"),
            (30, "PRN23EC089", "Negha Biju"),
            (39, "PRN23EC098", "Sarang Vinod"),
        ]
        conn = get_connection()
        conn.executemany(
            "INSERT INTO students (roll_no, student_id, student_name) VALUES (?, ?, ?)",
            students
        )
        conn.commit()
        conn.close()
        print(f"Added {len(students)} students to master list.")
    else:
        print("Students already seeded, skipping.")


def get_all_students():
    conn = get_connection()
    students = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    conn.close()
    return students


def get_attendance_with_absent(subject, date_filter):
    conn = get_connection()
    students = conn.execute("SELECT * FROM students ORDER BY roll_no").fetchall()
    present_ids = set(row["student_id"] for row in conn.execute("""
        SELECT DISTINCT student_id FROM attendance
        WHERE subject = ? AND date = ?
    """, (subject, date_filter)).fetchall())
    conn.close()

    result = []
    for s in students:
        result.append({
            "roll_no":      s["roll_no"],
            "student_id":   s["student_id"],
            "student_name": s["student_name"],
            "status":       "Present" if s["student_id"] in present_ids else "Absent"
        })
    return result


# ── TEACHER FUNCTIONS ─────────────────────────────────────────────────────────

def add_teacher(name, subject):
    conn = get_connection()
    conn.execute("INSERT INTO teachers (name, subject) VALUES (?, ?)", (name, subject))
    conn.commit()
    conn.close()


def get_all_teachers():
    conn = get_connection()
    teachers = conn.execute("SELECT * FROM teachers").fetchall()
    conn.close()
    return teachers


def get_subjects():
    conn = get_connection()
    subjects = conn.execute("SELECT DISTINCT subject FROM teachers").fetchall()
    conn.close()
    return [row["subject"] for row in subjects]


# ── ATTENDANCE FUNCTIONS ──────────────────────────────────────────────────────

def mark_attendance(student_id, student_name, subject, marked_by, session_id):
    today = date.today().strftime("%Y-%m-%d")
    now   = datetime.now().strftime("%H:%M:%S")
    conn  = get_connection()

    existing = conn.execute("""
        SELECT id FROM attendance
        WHERE student_id = ? AND session_id = ?
    """, (student_id, session_id)).fetchone()

    if existing:
        conn.close()
        return False

    conn.execute("""
        INSERT INTO attendance (session_id, student_id, student_name, subject, date, time, marked_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, student_id, student_name, subject, today, now, marked_by))
    conn.commit()
    conn.close()
    return True


def get_attendance(subject=None, date_filter=None):
    conn   = get_connection()
    query  = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if subject:
        query += " AND subject = ?"
        params.append(subject)
    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)

    query += " ORDER BY date DESC, time DESC"
    records = conn.execute(query, params).fetchall()
    conn.close()
    return records


def delete_attendance(record_id):
    conn = get_connection()
    conn.execute("DELETE FROM attendance WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def update_attendance(record_id, student_id, student_name, subject, date_val, time_val):
    conn = get_connection()
    conn.execute("""
        UPDATE attendance
        SET student_id=?, student_name=?, subject=?, date=?, time=?
        WHERE id=?
    """, (student_id, student_name, subject, date_val, time_val, record_id))
    conn.commit()
    conn.close()


# ── SEED DEFAULT TEACHERS ─────────────────────────────────────────────────────

def seed_default_teachers():
    conn  = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
    conn.close()

    if count == 0:
        default_teachers = [
            ("Chithra Ravindran", "EMT"),
            ("Smrithi V",         "VLSI"),
            ("Jenny Patrick",     "ITC"),
            ("Sudheer V R",       "MEMS"),
            ("Sandeep E",         "Management of Engineers"),
            ("Arun P L",          "Communication Lab"),
            ("Jasna K",           "Comprehensive Course Work"),
            ("Sudheer V R",       "Mini Project"),
        ]
        for name, subject in default_teachers:
            add_teacher(name, subject)
        print(f"Added {len(default_teachers)} default teachers.")
    else:
        print("Teachers already exist, skipping.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nInitializing database...")
    init_db()
    seed_students()
    seed_default_teachers()

    print("\nStudents:")
    for s in get_all_students():
        print(f"  Roll {s['roll_no']} — {s['student_name']} ({s['student_id']})")

    print("\nDatabase ready!")


# ── MANUAL CORRECTION FUNCTIONS ───────────────────────────────────────────────

def manual_mark_present(student_id, student_name, subject, date_val, session_id):
    """Manually mark a student present for a given subject and date."""
    now  = datetime.now().strftime("%H:%M:%S")
    conn = get_connection()

    existing = conn.execute("""
        SELECT id FROM attendance
        WHERE student_id = ? AND session_id = ?
    """, (student_id, session_id)).fetchone()

    if existing:
        conn.close()
        return False  # Already marked

    conn.execute("""
        INSERT INTO attendance (session_id, student_id, student_name, subject, date, time, marked_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (session_id, student_id, student_name, subject, date_val, now, "Manual"))
    conn.commit()
    conn.close()
    return True


def manual_remove_present(student_id, subject, date_val):
    """Remove a student's attendance record for a given subject and date."""
    conn = get_connection()
    conn.execute("""
        DELETE FROM attendance
        WHERE student_id = ? AND subject = ? AND date = ?
    """, (student_id, subject, date_val))
    conn.commit()
    conn.close()


# ── REPORT FUNCTIONS ──────────────────────────────────────────────────────────

def get_all_subjects_with_class_count():
    """Returns each subject and how many unique class dates were held."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT subject, COUNT(DISTINCT session_id) as total_classes
        FROM attendance
        GROUP BY subject
    """).fetchall()
    conn.close()
    return {row["subject"]: row["total_classes"] for row in rows}


def get_student_report(student_id):
    """
    Returns attendance report for a single student across all subjects.
    Shows classes attended, total classes held, and percentage.
    """
    conn = get_connection()

    # Get student info
    student = conn.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()

    if not student:
        conn.close()
        return None, []

    # Get all subjects and their total class counts
    subject_totals = conn.execute("""
        SELECT subject, COUNT(DISTINCT session_id) as total_classes
        FROM attendance
        GROUP BY subject
    """).fetchall()

    # Get classes this student attended per subject
    attended = conn.execute("""
        SELECT subject, COUNT(*) as attended
        FROM attendance
        WHERE student_id = ?
        GROUP BY subject
    """, (student_id,)).fetchall()

    attended_map = {row["subject"]: row["attended"] for row in attended}

    conn.close()

    report = []
    for row in subject_totals:
        subject      = row["subject"]
        total        = row["total_classes"]
        att          = attended_map.get(subject, 0)
        percentage   = round((att / total) * 100) if total > 0 else 0

        if percentage >= 75:
            status = "good"
        elif percentage >= 60:
            status = "warning"
        else:
            status = "danger"

        report.append({
            "subject":    subject,
            "attended":   att,
            "total":      total,
            "percentage": percentage,
            "status":     status
        })

    return dict(student), report