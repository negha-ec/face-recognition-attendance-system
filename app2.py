"""
Flask App — Attendance System (sub folder version)
====================================================
Usage:
    python3 app2.py
Then open: http://127.0.0.1:5002
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import face_recognition
import cv2
import pickle
import numpy as np
import threading
import pandas as pd
import os
import uuid
from datetime import date
from database2 import init_db, seed_students, get_subjects, mark_attendance, get_attendance, \
                      delete_attendance, update_attendance, get_attendance_with_absent, \
                      manual_mark_present, manual_remove_present, \
                      get_all_students, get_student_report

# ── CONFIG ───────────────────────────────────────────────────────────────────
ENCODINGS_FILE = "encodings.pkl"
TOLERANCE      = 0.5
SCALE          = 0.5
MODEL          = "hog"
PORT           = 5002
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder="templates")

camera_state = {
    "running":      False,
    "subject":      None,
    "marked":       [],
    "start_camera": False,
    "session_id":   None,
}

print("Loading encodings...", end=" ")
with open(ENCODINGS_FILE, "rb") as f:
    known_data = pickle.load(f)
print(f"Loaded {len(known_data['encodings'])} encodings.\n")


# ── CAMERA (main thread) ──────────────────────────────────────────────────────

def run_camera(subject):
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        camera_state["running"] = False
        return

    print(f"\nCamera opened for subject: {subject}")
    print("Press Q to stop.\n")

    while camera_state["running"]:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        small = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
        rgb   = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb, model=MODEL)
        face_encodings = face_recognition.face_encodings(rgb, face_locations)

        for (top, right, bottom, left), encoding in zip(face_locations, face_encodings):
            matches   = face_recognition.compare_faces(known_data["encodings"], encoding, tolerance=TOLERANCE)
            distances = face_recognition.face_distance(known_data["encodings"], encoding)

            name = "Unknown"; student_id = ""; confidence = 0

            if True in matches:
                best = np.argmin(distances)
                if matches[best]:
                    name       = known_data["names"][best]
                    student_id = known_data["ids"][best]
                    confidence = int((1 - distances[best]) * 100)

                    if name not in camera_state["marked"]:
                        if mark_attendance(student_id, name, subject, marked_by="Auto", session_id=camera_state["session_id"]):
                            camera_state["marked"].append(name)
                            print(f"  ✓ Marked: {name} ({student_id})")

            top    = int(top    / SCALE)
            right  = int(right  / SCALE)
            bottom = int(bottom / SCALE)
            left   = int(left   / SCALE)

            color = (0, 200, 0) if name != "Unknown" else (0, 0, 220)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom), (right, bottom + 45), color, -1)
            cv2.putText(frame, name, (left + 5, bottom + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            if name != "Unknown":
                cv2.putText(frame, f"{student_id}  {confidence}%",
                            (left + 5, bottom + 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        cv2.putText(frame, f"Subject: {subject}   Marked: {len(camera_state['marked'])}   Press Q to stop",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        cv2.imshow("Attendance System — Press Q to Stop", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            camera_state["running"] = False
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\nCamera closed.")


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    subjects = get_subjects()
    today    = date.today().strftime("%B %d, %Y")
    return render_template("index2.html", subjects=subjects, today=today)


@app.route("/start", methods=["POST"])
def start():
    subject = request.form.get("subject")
    if not subject:
        return redirect(url_for("index"))
    camera_state["running"]      = True
    camera_state["subject"]      = subject
    camera_state["marked"]       = []
    camera_state["session_id"]   = str(uuid.uuid4())[:8]
    camera_state["start_camera"] = True
    return render_template("camera2.html", subject=subject)


@app.route("/marked_students")
def marked_students():
    return jsonify({
        "marked":  camera_state["marked"],
        "running": camera_state["running"]
    })


@app.route("/stop", methods=["POST"])
def stop():
    camera_state["running"] = False
    return redirect(url_for("view_attendance", subject=camera_state["subject"]))


@app.route("/attendance")
def view_attendance():
    subject     = request.args.get("subject", "")
    date_filter = request.args.get("date", "")
    subjects    = get_subjects()
    records     = get_attendance(subject or None, date_filter or None)
    today       = date.today().strftime("%Y-%m-%d")
    return render_template("attendance2.html",
                           records=records,
                           subjects=subjects,
                           selected_subject=subject,
                           selected_date=date_filter,
                           today=today)


@app.route("/delete/<int:record_id>", methods=["POST"])
def delete_record(record_id):
    subject = request.form.get("subject", "")
    delete_attendance(record_id)
    return redirect(url_for("view_attendance", subject=subject))


@app.route("/attendance_status")
def attendance_status():
    subject     = request.args.get("subject", "")
    date_filter = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    filter_type = request.args.get("filter", "all")
    subjects    = get_subjects()
    records     = get_attendance_with_absent(subject, date_filter) if subject else []
    today       = date.today().strftime("%Y-%m-%d")
    import uuid
    session_id = str(uuid.uuid4())[:8]
    return render_template("attendance_status2.html",
                           records=records,
                           subjects=subjects,
                           selected_subject=subject,
                           selected_date=date_filter,
                           filter_type=filter_type,
                           today=today,
                           session_id=session_id)


@app.route("/mark_present", methods=["POST"])
def mark_present():
    student_id   = request.form.get("student_id")
    student_name = request.form.get("student_name")
    subject      = request.form.get("subject")
    date_val     = request.form.get("date")
    filter_type  = request.form.get("filter", "all")
    session_id = request.form.get("session_id", str(uuid.uuid4())[:8])
    manual_mark_present(student_id, student_name, subject, date_val, session_id)
    return redirect(url_for("attendance_status",
                            subject=subject, date=date_val, filter=filter_type))


@app.route("/remove_present", methods=["POST"])
def remove_present():
    student_id  = request.form.get("student_id")
    subject     = request.form.get("subject")
    date_val    = request.form.get("date")
    filter_type = request.form.get("filter", "all")
    manual_remove_present(student_id, subject, date_val)
    return redirect(url_for("attendance_status",
                            subject=subject, date=date_val, filter=filter_type))



@app.route("/reports")
def reports():
    from database2 import get_all_students
    students = get_all_students()
    subjects = get_subjects()
    return render_template("reports2.html", students=students, subjects=subjects)


@app.route("/student_report/<student_id>")
def student_report(student_id):
    student, report = get_student_report(student_id)
    if not student:
        return redirect(url_for("reports"))
    return render_template("student_report2.html", student=student, report=report)



@app.route("/export")
def export_excel():
    subject     = request.args.get("subject", "")
    date_filter = request.args.get("date", "")
    records     = get_attendance(subject or None, date_filter or None)

    rows = [{
        "Student ID":   r["student_id"],
        "Student Name": r["student_name"],
        "Subject":      r["subject"],
        "Date":         r["date"],
        "Time":         r["time"],
        "Marked By":    r["marked_by"]
    } for r in records]

    df       = pd.DataFrame(rows)
    filename = f"attendance_{subject or 'all'}_{date.today()}.xlsx"
    filepath = f"static/{filename}"
    os.makedirs("static", exist_ok=True)
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True, download_name=filename)


@app.route("/export_status")
def export_status():
    subject     = request.args.get("subject", "")
    date_filter = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    filter_type = request.args.get("filter", "all")
    all_records = get_attendance_with_absent(subject, date_filter)

    if filter_type == "present":
        records = [r for r in all_records if r["status"] == "Present"]
    elif filter_type == "absent":
        records = [r for r in all_records if r["status"] == "Absent"]
    else:
        records = all_records

    rows = [{
        "Roll No":      r["roll_no"],
        "Student ID":   r["student_id"],
        "Student Name": r["student_name"],
        "Status":       r["status"]
    } for r in records]

    df       = pd.DataFrame(rows)
    filename = f"attendance_{subject}_{date_filter}_{filter_type}.xlsx"
    filepath = f"static/{filename}"
    os.makedirs("static", exist_ok=True)
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True, download_name=filename)


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    seed_students()

    flask_thread = threading.Thread(
        target=lambda: app.run(debug=False, threaded=True, port=PORT),
        daemon=True
    )
    flask_thread.start()

    print("\n========================================")
    print("  Attendance System Running!")
    print(f"  Open your browser: http://127.0.0.1:{PORT}")
    print("========================================\n")
    print("Waiting for attendance session to start...\n")

    while True:
        if camera_state["start_camera"]:
            camera_state["start_camera"] = False
            run_camera(camera_state["subject"])
        cv2.waitKey(100)