"""
Live Face Recognition Script
==============================
Opens the camera, detects all faces in the frame,
matches them against encodings.pkl, and displays names.

This is a TEST script to verify recognition is working
before connecting it to the attendance system.

Usage:
    python3 recognize_faces.py

Controls:
    Q — quit
"""

import face_recognition
import cv2
import pickle
import numpy as np

# ── CONFIG ──────────────────────────────────────────────────────────────────
ENCODINGS_FILE = "encodings.pkl"
TOLERANCE = 0.5        # lower = stricter matching (0.4–0.6 is ideal)
SCALE = 0.5            # shrink frame for faster processing (don't change)
MODEL = "hog"          # "hog" = fast (CPU), "cnn" = accurate (needs GPU)
# ────────────────────────────────────────────────────────────────────────────


def load_encodings():
    print("Loading encodings...", end=" ")
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"Loaded {len(data['encodings'])} encodings for {len(set(data['names']))} students.\n")
    return data


def recognize_faces():
    data = load_encodings()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Could not open camera.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("Camera started. Press Q to quit.\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # Shrink frame for faster face detection
        small_frame = cv2.resize(frame, (0, 0), fx=SCALE, fy=SCALE)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # Detect face locations and encodings in current frame
        face_locations = face_recognition.face_locations(rgb_small, model=MODEL)
        face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):

            # Compare this face against all known encodings
            matches = face_recognition.compare_faces(
                data["encodings"], face_encoding, tolerance=TOLERANCE
            )
            face_distances = face_recognition.face_distance(
                data["encodings"], face_encoding
            )

            name = "Unknown"
            student_id = ""
            confidence = 0

            if True in matches:
                # Pick the closest match
                best_index = np.argmin(face_distances)
                if matches[best_index]:
                    name = data["names"][best_index]
                    student_id = data["ids"][best_index]
                    confidence = int((1 - face_distances[best_index]) * 100)

            # Scale face location back to original frame size
            top    = int(top    / SCALE)
            right  = int(right  / SCALE)
            bottom = int(bottom / SCALE)
            left   = int(left   / SCALE)

            # Choose box color — green for known, red for unknown
            color = (0, 200, 0) if name != "Unknown" else (0, 0, 220)

            # Draw box around face
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Draw label background
            cv2.rectangle(frame, (left, bottom), (right, bottom + 45), color, -1)

            # Draw name and confidence
            cv2.putText(frame, name, (left + 5, bottom + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

            if name != "Unknown":
                cv2.putText(frame, f"{student_id}  {confidence}%",
                            (left + 5, bottom + 38),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        # Show face count
        cv2.putText(frame, f"Faces detected: {len(face_locations)}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow("Face Recognition - Press Q to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("Camera closed.")


if __name__ == "__main__":
    recognize_faces()