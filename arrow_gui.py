##This is a simple utility for DDR so I can track play time AND calories burned

import keyboard
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import time
#import csv #elected to go with json instead of csv to track songs and biometrics
import json 
import xml.etree.ElementTree as ET #needed for pulling information from stepmania XML file data
from datetime import datetime, timedelta
import os #needed to access files for saving json
import threading
import asyncio #needed for xml try / for
from bleak import BleakClient #needed to connect to bt hr monitor
import pygame #needed for dance pad listening





steps = 0  #steps creates a variable that we can count steps into.
previous_step_count = 0 #global for step per min gui 
elapsed_time = 0 #global time variable used
calories_from_steps = 0.0 #need 2 calorie counters so I can add up both steps and basal calorie stuff
calories_from_hr = 0.0 #this creates a variable for us to count in our calories burned from heart rate using Male formula from Keytel paper
calories_per_step = 0.05 #calories_per_step is a made up number we assign to each step to get an estimated calorie count when multiplied by step count
start_time = None #start_time starts at 'None' so we can 'turn it on' when we are ready to dance!
tracking = False # tracking starts as false because we dont want the calorie counter to start until we are ready to dance (just like the timer)
paused = False #adding a pause button incase of... emergencies :)
session_start = None
session_end = None

#HR variables
bpm = 0 #creates a variable for our heart rate readings from BT monitor
hr_readings = [] #creates an array of heart rate readings to be used for calculating avg and max bpm
hr_time_series = [] #creates an array for more hear rate readings with time component!
bpm_interval_ms = 5000 #interval for refresh 5,000= 5 seconds 10,000 = 10 seconds
#moving_average_interval = 10000
max_bpm = 0 #creats variable for the maximum BPM
#average_bpm = 0 # lol similar to above but for average bpm

#Bleak Variables
client = None
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb" #This is a device specific code for the BT heart rate monitor i purchased
device_address = "F9:2D:CB:FD:CD:87" #specific address for BT device. If this gets lost use blue_tooth_find.py

#I want to look into summary csv at some point
#session specific variables
timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
session_id = f"session_{timestamp}"
json_format = "version 1.2"
json_format_update_date = "2025-07-13" #date format updated for consistency #ISO8601Gang4Lyfe
dance_pad = "OSTENT EVA/PVC" #metal pad is "LTEK Prime Metal"
event_log = []



# GUI colors ** maybe I can add a profile for 'green screen mode' to chroma key out gui
BG_GRADIENT = "#6dcfff"
TEXT_COLOR = "#ffffff"
ACCENT = "#e754c2"

#this creates our text for our GUI elements. we have a step_label and a calorie_label
def update_labels():
    global calories_from_steps, calories_from_hr
    total_calories = calories_from_steps + calories_from_hr
    step_label.config(text=f"Steps: {steps}")
    calorie_label.config(text=f"Calories: {total_calories:.2f}")

def update_hr_label():
    hr_label.config(text=f"Heart Rate: {bpm} bpm")

def handle_hr_data(_, data):
    global bpm, max_bpm, hr_readings
    bpm = data[1]  
    if bpm > 0:
        hr_readings.append(bpm) #stores max HR
        if bpm > max_bpm:
            max_bpm = bpm
    update_hr_label()

def log_event(event_type, elapsed_seconds):
    global event_log
    event_log.append({
        "type": event_type,
        "clock_time": datetime.now().strftime("%H:%M:%S"),
        "elapsed_seconds": elapsed_seconds       
    })

#handles heart rate and steps per minute data
def log_hr_over_time():
    global previous_step_count

    if tracking and not paused and bpm > 0:
        current_time = datetime.now().strftime("%H:%M:%S")
        interval_seconds = bpm_interval_ms / 1000

        #calculate short-term steps per minute
        steps_in_interval = steps - previous_step_count
        interval_steps_per_minute = steps_in_interval * (60 / interval_seconds)

        #update previous step count
        previous_step_count = steps

        #calculate average SPM 
        avg_steps_per_minute = (steps / elapsed_time) * 60 if elapsed_time > 0 else 0

        # Append to time series **Switched back to a dictionary for easier intergration with r and tidyverse
        hr_time_series.append({
            "session_id": session_id,
            "clock_time": current_time,
            "elapsed_seconds": elapsed_time,
            "bpm": bpm,
            "steps_per_minute": round(avg_steps_per_minute, 2),
            "sequence": len(hr_time_series) + 1 #just some extra bloat. fall back if elapsed_seconds runs into issues
        })

        # Update GUI display with real-time SPM
        steps_per_minute_label.config(text=f"Steps/min: {round(interval_steps_per_minute, 2)}")

    root.after(bpm_interval_ms, log_hr_over_time) #reruns log_hr_over_time dependant on an interval time

def calculate_calories_per_second(hr, weight_kg, age):
    # Male formula (Keytel et al., 2005 https://pubmed.ncbi.nlm.nih.gov/15966347/ Worth a read!)
    calories_per_min = (-55.0969 + (0.6309 * hr) + (0.1988 * weight_kg) + (0.2017 * age)) / 4.184
    return max(calories_per_min / 60, 0)

def format_elapsed_time(seconds):
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hrs:02}:{mins:02}:{secs:02}"

#this function has a break down of how we want the timer to display time.
def update_timer():
    global calories_from_hr, elapsed_time
    if tracking and not paused and start_time is not None:
        elapsed_time += 1
        timer_label.config(text=f"Time: {format_elapsed_time(elapsed_time)}")

        #this function handles our 2 intermediate calorie values to give us a total calorie count
        if bpm > 0:
            calories_this_second = calculate_calories_per_second(bpm, weight_kg, age)
            calories_from_hr += calories_this_second
            
            total_calories = calories_from_steps + calories_from_hr
            calorie_label.config(text=f"Calories: {total_calories:.2f}")

    root.after(1000, update_timer)

#this takes an arrow press and adds a +1 into steps.
def on_arrow_press(event):
    global steps, calories_from_steps
    if tracking and not paused:
        steps += 1
        calories_from_steps = steps * calories_per_step  # Only counts calories from steps with our made up magic number
        update_labels()

def on_enter_press(event):
    if tracking and not paused:
        log_event("you hit enter", elapsed_time)

#this is what my start button activates when pressed! It begins the timer and step tracker
#***Do I want a pause button?
def start_tracking():
    global start_time, tracking, elapsed_time, steps, session_start
    steps = 0
    elapsed_time = 0
    start_time = time.time()
    session_start = datetime.now()
    tracking = True
    update_labels()
    start_btn.config(state="disabled", bg="#666")

def get_stepmania_session_songs():
    global session_start, session_end
    try:
        stepmania_stats_path = os.path.expanduser(
            r"C:\Users\typec\AppData\Roaming\StepMania 5\Save\LocalProfiles\00000000\Stats.xml"
        )
        tree = ET.parse(stepmania_stats_path)
        root = tree.getroot()
        songs = []

        for song in root.findall(".//Song"):
            song_path = song.attrib.get("Dir", "Unknown Song")

            for steps in song.findall(".//Steps"):
                highscore_list = steps.find("HighScoreList")
                if highscore_list is None:
                    continue

                highscore = highscore_list.find("HighScore")
                if highscore is None:
                    continue

                datetime_text = highscore.findtext("DateTime")
                if not datetime_text:
                    continue

                try:
                    song_datetime = datetime.strptime(datetime_text, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue

                if session_start is None or session_end is None:
                    continue
                if not (session_start <= song_datetime <= session_end):
                    continue

                difficulty = steps.attrib.get("Difficulty", "Unknown")
                score = highscore.findtext("Score")

                #parse duration and calculate start time (if possible)
                raw_duration = highscore.findtext("SurviveSeconds")
                try:
                    duration = float(raw_duration) if raw_duration else None
                except ValueError:
                    duration = None

                if duration:
                    try:
                        start_time = song_datetime - timedelta(seconds=duration)
                    except Exception:
                        start_time = None
                else:
                    start_time = None

                # Tap note breakdown
                tap_scores = highscore.find("TapNoteScores")
                miss = tap_scores.findtext("Miss") if tap_scores is not None else None
                boo = tap_scores.findtext("W5") if tap_scores is not None else None
                good = tap_scores.findtext("W4") if tap_scores is not None else None
                great = tap_scores.findtext("W3") if tap_scores is not None else None
                perfect = tap_scores.findtext("W2") if tap_scores is not None else None
                flawless = tap_scores.findtext("W1") if tap_scores is not None else None

                #compute elapsed seconds from session start to song end
                end_time_elapsed = (song_datetime - session_start).total_seconds() if session_start and song_datetime else None
                start_time_elapsed = (end_time_elapsed - duration) if end_time_elapsed and duration else None

                songs.append({
                    "session_id": session_id,
                    "song": os.path.basename(os.path.normpath(song_path)),
                    "difficulty": difficulty,
                    "score": score,
                    "duration": duration,
                    "end_time": song_datetime.strftime("%H:%M:%S"),
                    "end_time_elapsed": round(end_time_elapsed, 2) if end_time_elapsed is not None else None,
                    "start_time_elapsed": round(start_time_elapsed, 2) if start_time_elapsed is not None else None,
                    "miss": miss,
                    "boo": boo,
                    "good": good,
                    "great": great,
                    "perfect": perfect,
                    "flawless": flawless
                })

        return songs

    except Exception as error:
        print(f"Error reading StepMania stats: {error}")
        return []


def save_to_json():
    global elapsed_time, session_end
    if not tracking or start_time is None:
        messagebox.showinfo("Info", "No session data to save.")
        return

    #elapsed = int(time.time() - start_time) global variable now: elapsed_time
    duration = format_elapsed_time(elapsed_time)
    session_end = datetime.now()
    average_bpm = round(sum(hr_readings) / len(hr_readings), 2) if hr_readings else 0

    #where json lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(base_dir, "ddr_sessions")
    os.makedirs(save_dir, exist_ok=True)

    #file name: timestamped
    default_name = f"DDR_Session_{timestamp}.json" 
    filename = os.path.join(save_dir, default_name)

    #get a data
    song_data = get_stepmania_session_songs()

    #preventing devides by zero issues
    safe_elapsed = elapsed_time if elapsed_time > 0 else 1
    safe_song_count = len(song_data) if song_data else 1

    #nerdy stats to play with later
    step_density = steps / safe_elapsed  # steps per second
    avg_steps_per_song = steps / safe_song_count
    session_intensity = average_bpm * step_density  # made-up but fun metric

    session_information = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "json_version": json_format,
    "json_format_update_date": json_format_update_date,
    "dance_pad_type": dance_pad
    }

    biometrics_data = {
    "weight_kg": weight_kg,
    "age": age,
    "steps": steps,
    "songs_played_count": safe_song_count, #I put this in biometrics because I think it will be helpful down the line for data manipulation even though I think it should go in session info
    "elapsed_seconds":elapsed_time,
    "formatted_duration": duration,
    "average_bpm": average_bpm,
    "max_bpm": max_bpm,
    #"bpm_interval_header": ["timestamp", "elapsed_seconds", "bpm", "steps_per_minute"], #no longer needed bpm_interval is now a dictionary instead of an array
    "total_calories": round(calories_from_hr + calories_from_steps, 2),
    "calories_from_steps": round(calories_from_steps, 2),
    "calories_from_hr": round(calories_from_hr, 2),
    "step_density_per_second": round(step_density, 3),
    "avg_steps_per_song": round(avg_steps_per_song, 2),
    "session_intensity": round(session_intensity, 2)
    }

    session_steps_rating = {
    "flawless": 0,
    "perfect": 0,
    "great": 0,
    "good": 0,
    "boo": 0,
    "miss": 0,
    "total_dance_steps": 0
    }

    #iterates through our songs (array?) object and counts the quality of step in song for total session
    for song in song_data:
        session_steps_rating["flawless"] += int(song.get("flawless", 0) or 0)
        session_steps_rating["perfect"] += int(song.get("perfect", 0) or 0)
        session_steps_rating["great"] += int(song.get("great", 0) or 0)
        session_steps_rating["good"] += int(song.get("good", 0) or 0)
        session_steps_rating["boo"] += int(song.get("boo", 0) or 0)
        session_steps_rating["miss"] += int(song.get("miss", 0) or 0)

    #adds up all steps except misses (this is different than our steps above that will count menu presses etc.)
    #this is import for our accuracy statistic
    total_dance_steps = (
        session_steps_rating["flawless"] +
        session_steps_rating["perfect"] +
        session_steps_rating["great"] +
        session_steps_rating["good"] +
        session_steps_rating["boo"]
    )
    
    #creates an accuracy statistic
    denominator = total_dance_steps + session_steps_rating["miss"]
    overall_accuracy = 100 * total_dance_steps / denominator if denominator > 0 else 0.0 #ugh okay I would rather do this than have it get borqed

    #this is a stricter accuracy that focuses on the steps that retain combos in step mania 'flawless, perfect, great' the above accuracy has been giving me scores that are too high lol
    combo_accuracy = 100 * (session_steps_rating["flawless"] + session_steps_rating["perfect"] + session_steps_rating["great"]) / denominator if denominator > 0 else 0.0

    #adds the above count of total steps to json
    session_steps_rating["total_dance_steps"] = total_dance_steps
    session_steps_rating["overall_accuracy"] = overall_accuracy
    session_steps_rating["combo_accuracy_fpg"] = combo_accuracy
    
    # jason data structure
    session_data = {
        "session_id": session_id,
        # "json_version": json_format,
        "session_information": session_information,
        "event_log": event_log,
        "biometrics": biometrics_data,
        "hr_time_series": hr_time_series,
        "songs": song_data,
        "session_steps": session_steps_rating
    }

    # write to file
    try:
        with open(filename, "w") as f:
            json.dump(session_data, f, indent=4) #the array is very spacious want to see how it looks with other json save formats
            #json.dump(session_data, f, separators=(",", ":")) #yup NOPE do NOT like how that looks
        messagebox.showinfo("Saved", f"Session saved to:\n{filename}")
    except Exception as error:
        messagebox.showerror("Error", f"Failed to save session:\n{error}")

#this prompts me on close if I want to save to JSON
def on_close():
    if tracking and start_time is not None:
        if messagebox.askyesno("Save Session", "Would you like to save your session as a CSV before exiting?"):
            save_to_json()
    root.destroy()

#GUI setup
root = tk.Tk()
root.title("DDR Step Tracker")
root.geometry("720x420")
root.configure(bg=BG_GRADIENT)
root.protocol("WM_DELETE_WINDOW", on_close)  # Ask on close

#User entered variables ** I might change this its kinda annoying
weight_lbs = simpledialog.askfloat("Weight", "Enter your weight in lbs we can do the math:")
age = simpledialog.askinteger("Age", "Enter your age in years:")

if weight_lbs is None:
    weight_lbs = 175  # default thats around my weight
if age is None:
    age = 33  # default age for me 

weight_kg = weight_lbs * 0.45359237 #convert it into kg lol

#allows pause / unpause
def toggle_pause():
    global paused
    paused = not paused
    if paused:
        pause_btn.config(text="Resume", bg="#1abc9c")  #teal
        pause_indicator.config(text="PAUSED", fg="#ff00ff")  #purple
        log_event("pause", elapsed_time) 
    else:
        pause_btn.config(text="Pause", bg="#9b59b6")  #purple
        pause_indicator.config(text="")  #hide it
        log_event("resume", elapsed_time)

def update_connection_status(connected):
    if connected:
        connection_label.config(text="HR Monitor: Connected", fg="green")
    else:
        connection_label.config(text="HR Monitor: Not connected", fg="red")


###
### GUI BEGINS ***

#main container
main_frame = tk.Frame(root, bg=BG_GRADIENT)
main_frame.pack(padx=20, pady=20)

#first row: steps and calories
row1 = tk.Frame(main_frame, bg=BG_GRADIENT)
row1.pack(fill="x", pady=5)

step_label = tk.Label(row1, text="Steps: 0", font=("Helvetica", 18, "bold"),
                      bg=BG_GRADIENT, fg=ACCENT, width=15, anchor="w")
step_label.pack(side="left", padx=10)

calorie_label = tk.Label(row1, text="Calories: 0.00", font=("Helvetica", 16),
                         bg=BG_GRADIENT, fg=TEXT_COLOR, width=15, anchor="w")
calorie_label.pack(side="left", padx=10)

#second row time, HR, steps/min
row2 = tk.Frame(main_frame, bg=BG_GRADIENT)
row2.pack(fill="x", pady=5)

timer_label = tk.Label(row2, text="Time: 00:00:00", font=("Helvetica", 16),
                       bg=BG_GRADIENT, fg=TEXT_COLOR, width=15, anchor="w")
timer_label.pack(side="left", padx=10)

hr_label = tk.Label(row2, text="Heart Rate: -- bpm", font=("Helvetica", 16),
                    bg=BG_GRADIENT, fg=TEXT_COLOR, width=15, anchor="w")
hr_label.pack(side="left", padx=10)

steps_per_minute_label = tk.Label(row2, text="Steps/min: --", font=("Helvetica", 16),
                                  bg=BG_GRADIENT, fg=TEXT_COLOR, width=15, anchor="w")
steps_per_minute_label.pack(side="left", padx=10)

#bottom section connection + buttons
bottom_controls = tk.Frame(main_frame, bg=BG_GRADIENT)
bottom_controls.pack(fill="x", pady=10)

#a little spacer
tk.Label(bottom_controls, text="", bg=BG_GRADIENT, height=1).pack(pady=10)

connection_label = tk.Label(bottom_controls, text="HR Monitor: Not connected", font=("Helvetica", 14),
                            bg=BG_GRADIENT, fg="red")
connection_label.pack(pady=5)

pause_indicator = tk.Label(bottom_controls, text="", font=("Helvetica", 20, "bold"),
                           bg=BG_GRADIENT, fg="#ff00ff")  # hot pink / magenta
pause_indicator.pack(pady=5)

button_frame = tk.Frame(bottom_controls, bg=BG_GRADIENT)
button_frame.pack(pady=5)

start_btn = tk.Button(button_frame, text="Start", font=("Helvetica", 14, "bold"),
                      command=start_tracking, bg=ACCENT, fg="black",
                      activebackground="#d66fbe", activeforeground="white", width=15)
start_btn.pack(side="left", padx=10)

save_btn = tk.Button(button_frame, text="Save to JSON", font=("Helvetica", 12),
                     command=save_to_json, bg="#dddddd", fg="black", width=15)
save_btn.pack(side="left", padx=10)

pause_btn = tk.Button(button_frame, text="Pause", font=("Helvetica", 12),
                      command=toggle_pause, bg="#9b59b6", fg="white", width=15)
pause_btn.pack(side="left", padx=10)

###
### GUI ENDS

# Keyboard listeners (this will need to change when I get my DDR pad!)
# for key in ['up', 'down', 'left', 'right']:
#     keyboard.on_press_key(key, on_arrow_press)


# listener for enter so help track songs being played
keyboard.on_press_key('enter', on_enter_press)

#*****For crappy plastic pad
def ddr_listener():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No joystick detected.")
        return

    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    button_map = {
        0: "left",
        1: "down",
        2: "up",
        3: "right"
    }

    print(f"Listening for DDR pad input: {joystick.get_name()}")

    while True:
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                direction = button_map.get(event.button)
                if direction:
                    fake_event = type("Event", (object,), {"name": direction})()
                    on_arrow_press(fake_event)

#replace keyboard listener with threaded DDR listener
threading.Thread(target=ddr_listener, daemon=True).start()

#*** END for crappy plastic pad

#bluetooth connection and status function
def start_ble_loop():
    async def run():
        while True:
            try:
                print("Attempting to connect to HR monitor...")
                async with BleakClient(device_address) as client:
                    await client.start_notify(HR_MEASUREMENT_UUID, handle_hr_data)
                    update_connection_status(True)
                    print("Connected to HR monitor")

                    root.after(bpm_interval_ms, log_hr_over_time)

                    while True:
                        if not client.is_connected:
                            print("Disconnected from HR monitor")
                            update_connection_status(False)
                            break
                        await asyncio.sleep(1)

            except Exception as error:
                print("BLE Error occurred:")
                print(f"Type: {type(error).__name__}")
                print(f"BLE Error: {error}")
                update_connection_status(False)

            await asyncio.sleep(5)  # Wait before trying to reconnect

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())

threading.Thread(target=start_ble_loop, daemon=True).start()

def flash_pause_indicator():
    if paused:
        current_color = pause_indicator.cget("fg")
        new_color = "#ff00ff" if current_color == "#6dcfff" else "#6dcfff"
        pause_indicator.config(fg=new_color)
    root.after(500, flash_pause_indicator)  # change color every 0.5s

flash_pause_indicator()
update_timer()
root.mainloop()