"""
Face Encoding Script
======================
Reads all student photos from the dataset folder,
generates face encodings, and saves them to encodings.pkl

Run this once before starting the attendance system.
Re-run whenever you add a new student to the dataset.

Usage:
    python3 encode_faces.py
"""

import face_recognition
import os
import pickle

# ── CONFIG ──────────────────────────────────────────────────────────────────
DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings.pkl"
# ────────────────────────────────────────────────────────────────────────────


def encode_all_students():
    known_encodings = []
    known_names = []
    known_ids = []

    # Get list of all student folders
    student_folders = [
        f for f in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, f))
    ]

    if not student_folders:
        print("ERROR: No student folders found in dataset/")
        print("Make sure you have run collect_faces.py first.")
        return

    print(f"\nFound {len(student_folders)} student(s) in dataset.\n")

    for folder_name in student_folders:
        folder_path = os.path.join(DATASET_DIR, folder_name)

        # Extract student ID and name from folder name (e.g. CS21001_Rahul_Kumar)
        parts = folder_name.split("_", 1)
        student_id = parts[0]
        student_name = parts[1].replace("_", " ") if len(parts) > 1 else folder_name

        print(f"Processing: {student_name} ({student_id})")

        # Get all jpg images in this folder
        image_files = [
            f for f in os.listdir(folder_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if not image_files:
            print(f"  WARNING: No images found for {student_name}, skipping.")
            continue

        successful = 0
        for image_file in image_files:
            image_path = os.path.join(folder_path, image_file)

            # Load image
            image = face_recognition.load_image_file(image_path)

            # Get face encodings (returns list — could be 0 or more faces)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) == 0:
                # No face detected in this photo — skip it
                continue
            elif len(encodings) > 1:
                # Multiple faces in one photo — take the first one only
                encodings = [encodings[0]]

            known_encodings.append(encodings[0])
            known_names.append(student_name)
            known_ids.append(student_id)
            successful += 1

        print(f"  ✓ {successful}/{len(image_files)} photos encoded successfully")

    if not known_encodings:
        print("\nERROR: No faces could be encoded. Check your photos.")
        return

    # Save everything to a pickle file
    data = {
        "encodings": known_encodings,
        "names": known_names,
        "ids": known_ids
    }

    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

    print(f"\n========================================")
    print(f"  Encoding complete!")
    print(f"  Total encodings saved: {len(known_encodings)}")
    print(f"  Students encoded: {len(set(known_names))}")
    print(f"  Saved to: {ENCODINGS_FILE}")
    print(f"========================================")
    print(f"\nNext step: run  python3 recognize_faces.py")


if __name__ == "__main__":
    encode_all_students()