import firebase_admin
from firebase_admin import credentials, db, storage
from datetime import datetime
import cv2
import face_recognition
import numpy as np
import pickle
import os

# Initialize Firebase app
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://attendancesystem-9944a-default-rtdb.asia-southeast1.firebasedatabase.app/",
    'storageBucket': "attendancesystem-9944a.appspot.com"
})

ref = db.reference('Employee')
bucket = storage.bucket()


def get_next_id():
    employees = ref.get()
    if not employees:
        return "001"
    max_id = max(int(id) for id in employees.keys())
    return f"{max_id + 1:03d}"


def capture_face():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        cv2.imshow("Capture Face", frame)
        if cv2.waitKey(1) & 0xFF == ord('c'):
            face_locations = face_recognition.face_locations(frame)
            if face_locations:
                top, right, bottom, left = face_locations[0]

                # Add margin and ensure coordinates are within bounds
                margin = 40
                top = max(0, top - margin)
                right = min(frame.shape[1], right + margin)
                bottom = min(frame.shape[0], bottom + margin)
                left = max(0, left - margin)

                if bottom > top and right > left:
                    face_image = frame[top:bottom, left:right]
                    cv2.imshow("Captured Face", face_image)
                    cv2.waitKey(1000)
                    cap.release()
                    cv2.destroyAllWindows()
                    return face_image
                else:
                    print("Face coordinates out of bounds, please try again.")
        elif cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
    return None


def encode_face(face_image):
    rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(rgb_face)
    if encodings:
        return encodings[0]
    return None

def update_encodefile(new_encoding, employee_id):
    encodefile_path = "Encodefile.p"
    if os.path.exists(encodefile_path):
        with open(encodefile_path, 'rb') as file:
            encode_list_known_with_ids = pickle.load(file)

        if employee_id in encode_list_known_with_ids[1]:
            idx = encode_list_known_with_ids[1].index(employee_id)
            encode_list_known_with_ids[0][idx] = new_encoding
        else:
            encode_list_known_with_ids[0].append(new_encoding)
            encode_list_known_with_ids[1].append(employee_id)
    else:
        encode_list_known_with_ids = ([new_encoding], [employee_id])

    with open(encodefile_path, 'wb') as file:
        pickle.dump(encode_list_known_with_ids, file)

def upload_to_firebase_storage(face_image, employee_id):
    _, buffer = cv2.imencode('.jpg', face_image)
    image_bytes = buffer.tobytes()
    blob = bucket.blob(f'employee_faces/{employee_id}.jpg')
    blob.upload_from_string(image_bytes, content_type='image/jpeg')
    return blob.public_url

def add_employee(name=""):
    print("Please look at the camera and press 'c' to capture your face, or 'q' to quit.")
    face_image = capture_face()
    if face_image is None:
        print("Face capture cancelled or failed.")
        return None

    face_encoding = encode_face(face_image)
    if face_encoding is None:
        print("Failed to encode face. Please try again.")
        return None

    new_id = get_next_id()
    update_encodefile(face_encoding, new_id)

    image_url = upload_to_firebase_storage(face_image, new_id)

    new_employee = {
        "name": name,
        "total_attendance": 0,
        "last_attendance_time": datetime.now().strftime('%d-%m-%Y %H:%M:%S'),
        "daily_attendance": {},
        "daily_attendance_duration": "00:00:00",
        "face_image_url": image_url
    }
    ref.child(new_id).set(new_employee)
    print(f"Added employee: ID {new_id}, Name: {name}")
    return new_id


def remove_employee(employee_id):
    # Remove employee from Firebase database
    ref.child(employee_id).delete()

    # Remove employee's face image from Firebase Storage
    blob = bucket.blob(f'employee_faces/{employee_id}.jpg')
    blob.delete()

    # Remove employee's encoding from Encodefile.p
    encodefile_path = "Encodefile.p"
    if os.path.exists(encodefile_path):
        with open(encodefile_path, 'rb') as file:
            encode_list_known_with_ids = pickle.load(file)

        if employee_id in encode_list_known_with_ids[1]:
            idx = encode_list_known_with_ids[1].index(employee_id)
            del encode_list_known_with_ids[0][idx]
            del encode_list_known_with_ids[1][idx]

        with open(encodefile_path, 'wb') as file:
            pickle.dump(encode_list_known_with_ids, file)

    print(f"Removed employee: ID {employee_id}")

def add_multiple_employees(names):
    assigned_ids = []
    for name in names:
        assigned_id = add_employee(name)
        if assigned_id:
            assigned_ids.append(assigned_id)
    return assigned_ids

def update_employee_face(employee_id):
    print("Please look at the camera and press 'c' to capture your face, or 'q' to quit.")
    face_image = capture_face()
    if face_image is None:
        print("Face capture cancelled or failed.")
        return None

    face_encoding = encode_face(face_image)
    if face_encoding is None:
        print("Failed to encode face. Please try again.")
        return None

    # Update encoding in Encodefile.p
    update_encodefile(face_encoding, employee_id)

    # Update image in Firebase Storage
    image_url = upload_to_firebase_storage(face_image, employee_id)

    # Update the face image URL in Firebase database
    ref.child(employee_id).update({
        "face_image_url": image_url,
        "last_updated": datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    })

    print(f"Updated employee: ID {employee_id}")
    return employee_id

print("All employees added/updated successfully.")
