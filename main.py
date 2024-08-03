import os
import pickle
import cv2
import face_recognition
import time
import numpy as np
import cvzone
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from datetime import datetime, timedelta
import threading
import queue

cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': "https://attendancesystem-9944a-default-rtdb.asia-southeast1.firebasedatabase.app/",
    'storageBucket': "attendancesystem-9944a.appspot.com"
})

# Ask if user is using IP cam or webcam
choice = input("Are you using an IP Camera or Webcam? (Enter 'ip' or 'webcam'): ").lower()

#IP cam address
vid_url = 'rtsp://admin:UFQFVJ@192.168.10.224:554/H.264'

cap = None

if choice == 'ip':
    cap = cv2.VideoCapture(vid_url)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
elif choice == 'webcam':
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)
else:
    print("Invalid choice. Please run the program again and enter 'ip' or 'webcam'.")
    exit()

imgBackground = cv2.imread('Resources/background.png')

# Importing mode images into a list
folderModePath = 'Resources/Modes'
modePathList = os.listdir(folderModePath)
imgModeList = [cv2.imread(os.path.join(folderModePath, path)) for path in modePathList]

# load encode file
print("loading Encode File...")
with open('Encodefile.p', 'rb') as file:
    encodeListKnownWithIds = pickle.load(file)

encodeListKnown, Ids = encodeListKnownWithIds
print("Encode File Loaded")

modeType = 0
counter = 0
Id = -1
employeeInfo = None

output_dir = 'output'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

frame_count = 0
cooldown_period = 10
last_saved_time = time.time() - cooldown_period

# Frame skip counter
frame_counter = 0
FRAME_SKIP = 10

# Create a queue to hold frames
frame_queue = queue.Queue(maxsize=60)  # Adjust maxsize as needed

# Flag to signal the thread to stop
stop_thread = False

def capture_frames():
    global stop_thread
    while not stop_thread:
        success, img = cap.read()
        if not success:
            break
        if not frame_queue.full():
            frame_queue.put(img)
        else:
            # If queue is full, remove the oldest frame
            try:
                frame_queue.get_nowait()
            except queue.Empty:
                pass
            frame_queue.put(img)

# Start the capture thread
capture_thread = threading.Thread(target=capture_frames)
capture_thread.start()

def calculate_daily_attendance(attendance_times):
    if not attendance_times:
        return "00:00:00"

    # Convert string times to datetime objects
    times = [datetime.strptime(t, "%H:%M:%S") for t in attendance_times]

    # Find earliest and latest times
    earliest = min(times)
    latest = max(times)

    # Calculate duration
    duration = latest - earliest

    # Format duration
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def save_employee_image(employee_id, img):
    current_time = time.time()
    timestamp = time.strftime("%Y-%m-%d", time.localtime(current_time))
    frame_path = os.path.join(output_dir, f"{employee_id}_{timestamp}.jpg")
    cv2.imwrite(frame_path, img)
    return frame_path

# Define the desired resolution
desired_width = 640
desired_height = 480

while True:
    if frame_queue.empty():
        continue

    img = frame_queue.get()

    frame_counter += 1
    if frame_counter % FRAME_SKIP != 0:
        continue  # Skip this frame

    # Resize the frame to the desired resolution
    img = cv2.resize(img, (desired_width, desired_height))
    imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
    imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

    faceCurrentFrame = face_recognition.face_locations(imgS)
    encodeCurrentFrame = face_recognition.face_encodings(imgS, faceCurrentFrame)

    imgBackground[120:120 + 480, 78:78 + 640] = img
    imgBackground[110:110 + 500, 900:900 + 300] = imgModeList[modeType]

    if faceCurrentFrame:
        for encodeFace, faceLoc in zip(encodeCurrentFrame, faceCurrentFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)

            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:
                y1, x2, y2, x1 = faceLoc
                y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4

                bbox = 82 + x1, 125 + y1, x2 - (x1 + 10), y2 - (y1 + 10)
                imgBackground = cvzone.cornerRect(imgBackground, bbox, rt=0)
                Id = Ids[matchIndex]

                # # Save frame if not in cooldown
                # current_time = time.time()
                # if (current_time - last_saved_time >= cooldown_period):
                #     # Find ID
                #     matched_id = Id
                #
                #     # Format Time
                #     timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
                #
                #     # Name the file
                #     frame_path = os.path.join(output_dir, f"{matched_id}_at_{timestamp}.jpg")
                #     cv2.imwrite(frame_path, img)
                #     print(f"Saved: {frame_path}")
                #     last_saved_time = current_time

                if counter == 0:
                    counter = 1
                    modeType = 1

        if counter != 0:
            if counter == 1:
                employeeInfo = db.reference(f'Employee/{Id}').get()
                dateTimeObject = datetime.strptime(employeeInfo['last_attendance_time'],
                                                  "%d-%m-%Y %H:%M:%S")
                secondsElapsed = (datetime.now() - dateTimeObject).total_seconds()
                print(secondsElapsed)

                if secondsElapsed > 20:
                    ref = db.reference(f'Employee/{Id}')
                    ref.child('last_attendance_time').set(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    current_time = datetime.now().strftime("%H:%M:%S")

                    if 'daily_attendance' not in employeeInfo:
                        employeeInfo['daily_attendance'] = {}

                    if current_date not in employeeInfo['daily_attendance']:
                        employeeInfo['daily_attendance'][current_date] = []

                    # Increment total_attendance only once per day
                        if 'total_attendance' not in employeeInfo:
                            employeeInfo['total_attendance'] = 1
                        else:
                            employeeInfo['total_attendance'] += 1
                        ref.child('total_attendance').set(employeeInfo['total_attendance'])

                    # Add current time to the list of attendance times for today
                    current_time = datetime.now().strftime("%H:%M:%S")
                    employeeInfo['daily_attendance'][current_date].append(current_time)

                    # Update the database
                    ref.child('daily_attendance').update({current_date: employeeInfo['daily_attendance'][current_date]})

                    # Calculate daily attendance duration
                    daily_duration = calculate_daily_attendance(employeeInfo['daily_attendance'][current_date])
                    ref.child('daily_attendance_duration').set(daily_duration)

                    # Update last_attendance_time
                    ref.child('last_attendance_time').set(datetime.now().strftime("%d-%m-%Y %H:%M:%S"))

                    modeType = 1

                else:
                    modeType = 3
                    counter = 0
                    imgBackground[110:110 + 500, 900:900 + 300] = imgModeList[modeType]


            if modeType != 3:
                if 10 < counter < 20:
                    modeType = 2
                imgBackground[110:110 + 500, 900:900 + 300] = imgModeList[modeType]

                if counter <= 10 or counter >= 20:
                    latest_info = db.reference(f'Employee/{Id}').get()

                    daily_duration = latest_info.get('daily_attendance_duration', "00:00:00")
                    current_date = datetime.now().strftime("%Y-%m-%d")

                    # Get the attendance times for today and count them
                    attendance_times = latest_info.get('daily_attendance', {}).get(current_date, [])
                    today_attendance_count = len(attendance_times)

                    text_elements = [
                        f"Name: {str(latest_info['name'])}",
                        f"ID: {str(Id)}",
                        f"Total Attendances: {str(latest_info['total_attendance'])}",
                        f"Today's Attendances: {today_attendance_count}",
                        f"Last Attendance: {str(latest_info['last_attendance_time'])}",
                        f"Daily Attendance Duration: {daily_duration}",
                    ]

                    y_positions = [125, 150, 175, 200, 225, 250]  # Corresponding y positions for the text elements
                    font_scales = [0.5, 0.5, 0.5, 0.5, 0.4, 0.4]  # Corresponding font scales for the text elements

                    for i, text in enumerate(text_elements):
                        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_COMPLEX, font_scales[i], 1)
                        offset = (300 - w) // 2
                        x_position = 900 + offset  # Adjusted x_position for all text elements
                        cv2.putText(imgBackground, text, (x_position, y_positions[i]),
                                    cv2.FONT_HERSHEY_COMPLEX, font_scales[i], (0, 0, 0), 1)

            counter += 1

            if counter >= 20:
                counter = 0
                modeType = 0
                employeeInfo = []
                imgBackground[110:110 + 500, 900:900 + 300] = imgModeList[modeType]

    else:
        modeType = 0
        counter = 0

    cv2.imshow("Face attendance", imgBackground)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Signal the thread to stop
stop_thread = True

# Wait for the capture thread to finish
capture_thread.join()

cap.release()
cv2.destroyAllWindows()
