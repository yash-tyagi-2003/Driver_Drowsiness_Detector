import cv2
import dlib
import time
from playsound import playsound
from scipy.spatial import distance
import tkinter as tk
from PIL import Image, ImageTk
import pytz
import datetime
from twilio.rest import Client
import googlemaps
from pyfirmata import Arduino, util
import time
import pyfirmata


def motor_start(x, y, speed=0.706):
    board.digital[right_motor_pin1].write(x)
    board.digital[right_motor_pin2].write(y)
    board.digital[enable_right_motor].write(speed)


def calculate_EAR(eye):
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear


def submit_input():
    global phone
    phone_field.focus_set()
    phone = phone_field.get()
    phone_field.pack_forget()
    submit_button.pack_forget()
    start_button.pack(padx=10, pady=10)
    stop_button.pack(padx=10, pady=10)
    startj_button.pack(padx=10, pady=10)


def new_win():
    global s, d, sl, canvas1, new_window, info
    new_window = tk.Toplevel(window)
    new_window.title("Start Journey")
    sr = tk.Label(new_window, text="Enter Source Location : ")
    sr.pack()
    s = tk.Entry(new_window)
    s.pack()
    ds = tk.Label(new_window, text="Enter Destination Location : ")
    ds.pack()
    d = tk.Entry(new_window)
    d.pack()
    sleep = tk.Label(new_window, text="Enter your approx. Sleep Time : ")
    sleep.pack()
    sl = tk.Entry(new_window)
    sl.pack()
    submit = tk.Button(new_window, text="Submit", command=start_journey)
    submit.pack()
    info = tk.Label(new_window, text="")
    info.pack()
    canvas1 = tk.Canvas(new_window, width=canvas_width, height=canvas_height)
    canvas1.pack()


def send_location():
    account_sid = "AC25b930c7e6437c710c203704b73456c1"
    auth_token = "c2f4b394109bf710737ec47c047b1a53"
    api_key = "AIzaSyB578H3i9Rzhw5JzxbIfRH6zc9OF_s7lbE"

    gmaps = googlemaps.Client(key=api_key)
    client = Client(account_sid, auth_token)

    geo = gmaps.geolocate()
    latitude = geo["location"]["lat"]
    longitude = geo["location"]["lng"]

    message = client.messages.create(
        body=f"https://maps.google.com/maps?q={latitude},{longitude}",
        from_="+18149149507",
        to=str(phone)
    )


def start_journey():
    api_key = "AIzaSyB578H3i9Rzhw5JzxbIfRH6zc9OF_s7lbE"
    gmaps = googlemaps.Client(key=api_key)
    src = s.get()
    des = d.get()
    directions = gmaps.directions(src, des)
    dur = (directions[0]["legs"][0]["duration"]["text"])[:2]
    duration = dur[:2]
    print("Estimated Travel Time : ", duration)
    location_timezone = pytz.timezone('Asia/Kolkata')
    current_time = datetime.datetime.now(location_timezone)
    t = str(current_time)
    time = int(t[11:13])
    if (time > 0 and time < 5 or int(duration) > 5 or int(sl.get()) < 6):
        info.config(
            text="The time is " + t[11:19] + " and there is a high risk of Drowsiness during driving\n due to large Driving Duration of " + dur + " and " + sl.get() + " hours of sleep!!!\nStarting Drowsiness Detector..."
        )
        start(canvas1, new_window)
    else:
        info.config(text="You are ready to go...")


def start(canva, win):
    global is_running
    is_running = True
    motor_start(0, 1)
    flag = 0
    cap = cv2.VideoCapture(0)
    hog_face_detector = dlib.get_frontal_face_detector()
    dlib_facelandmark = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

    sleep_start_time = None
    drowsy_threshold = 0.26
    drowsy_confirmation_time = 2.0

    def detect_drowsiness():
        nonlocal sleep_start_time, flag

        ret, frame = cap.read()
        frame = cv2.flip(frame, 1)
        if not ret or not is_running:
            cap.release()
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = hog_face_detector(gray)

        for face in faces:
            face_landmarks = dlib_facelandmark(gray, face)
            leftEye = []
            rightEye = []

            for n in range(36, 42):
                x = face_landmarks.part(n).x
                y = face_landmarks.part(n).y
                leftEye.append((x, y))
                next_point = n + 1 if n < 41 else 36
                x2 = face_landmarks.part(next_point).x
                y2 = face_landmarks.part(next_point).y
                cv2.line(frame, (x, y), (x2, y2), (255, 255, 255), 2)
                cv2.circle(frame, (x, y), 2, (255, 0, 255), 4)

            for n in range(42, 48):
                x = face_landmarks.part(n).x
                y = face_landmarks.part(n).y
                rightEye.append((x, y))
                next_point = n + 1 if n < 47 else 42
                x2 = face_landmarks.part(next_point).x
                y2 = face_landmarks.part(next_point).y
                cv2.line(frame, (x, y), (x2, y2), (255, 255, 255), 2)
                cv2.circle(frame, (x, y), 2, (255, 0, 255), 4)

            lear = calculate_EAR(leftEye)
            rear = calculate_EAR(rightEye)

            EAR = (lear + rear) / 2
            EAR = round(EAR, 2)

            if EAR < drowsy_threshold:
                if sleep_start_time is None:
                    led1.write(0)
                    sleep_start_time = time.time()
                elif time.time() - sleep_start_time >= 1:
                    if time.time() - sleep_start_time >= 4:
                        flag += 1
                    cv2.putText(frame, "DROWSY", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 0), 4)
                    cv2.putText(frame, "Driver Sleeping", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 4)
                    print("Drowsy")
                    led1.write(1)
                    buz.write(1)
                    time.sleep(0.2)
                    buz.write(0)
                    playsound('beep-01a.wav')
            else:
                sleep_start_time = None
                flag = 0

            print(EAR)

            if flag == 1:
                xx = 1
                for i in range(700, 0, -100):
                    led2.write(1)
                    buz.write(1)
                    time.sleep(0.1)
                    led2.write(0)
                    buz.write(0)
                    time.sleep(0.1)
                    motor_start(0, 1, i / 1000)
                motor_start(0, 0)
                led2.write(1)
                send_location()

        frame = cv2.resize(frame, (canvas_width, canvas_height))
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        width, height = img.size
        aspect_ratio = min(canvas_width / width, canvas_height / height)

        new_width = int(width * aspect_ratio)
        new_height = int(height * aspect_ratio)

        img = img.resize((new_width, new_height), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(img)

        x = int((canvas_width - new_width) / 2)
        y = int((canvas_height - new_height) / 2)

        canva.img = img
        canva.create_image(x, y, anchor=tk.NW, image=img)

        if is_running:
            win.after(1, detect_drowsiness)
        else:
            cap.release()

    detect_drowsiness()


def stop():
    global is_running
    is_running = False
    canvas.delete("all")
    led1.write(0)
    led2.write(0)
    motor_start(0, 0)


def on_closing():
    stop()
    window.destroy()


# Create the main window
board = Arduino("/dev/cu.usbserial-110")
enable_right_motor = 3
right_motor_pin1 = 7
right_motor_pin2 = 8

board.digital[enable_right_motor].mode = pyfirmata.PWM
board.digital[right_motor_pin1].mode = pyfirmata.OUTPUT
board.digital[right_motor_pin2].mode = pyfirmata.OUTPUT
buz = board.get_pin('d:09:o')
led1 = board.get_pin('d:10:o')
led2 = board.get_pin('d:11:o')
window = tk.Tk()
window.title("Drowsiness Detection")
window.protocol("WM_DELETE_WINDOW", on_closing)

phone_field = tk.Entry(window)
phone_field.insert(0, "Enter Emergency Phone Number")
submit_button = tk.Button(window, text="Submit", command=submit_input, width=10, height=3)
phone_field.pack()
submit_button.pack()

# Create the Start and Stop buttons
startj_button = tk.Button(window, text="Start Journey", bg="green", command=new_win)
startj_button.pack_forget()

start_button = tk.Button(window, text="Start Drowsiness Detector", command=lambda: start(canvas, window))
start_button.pack_forget()

stop_button = tk.Button(window, text="Stop Drowsiness Detector", command=stop)
stop_button.pack_forget()

# Define the canvas size
canvas_width = 800
canvas_height = 600

# Create a canvas to display the camera frame
canvas = tk.Canvas(window, width=canvas_width, height=canvas_height)
canvas.pack()
is_running = False
window.mainloop()
