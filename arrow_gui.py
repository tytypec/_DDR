##This is a simple utility for DDR so I can track play time AND calories burned

import keyboard
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import time
#import csv #elected to go with json instead of csv to track songs and biometrics
import json 
import xml.etree.ElementTree as ET #needed for pulling information from stepmania XML file data
from datetime import datetime
import os #needed to access files for saving json
import threading
import asyncio #needed for xml try / for
from bleak import BleakClient #needed to connect to bt hr monitor





steps = 0  #steps creates a variable that we can count steps into.
calories_from_steps = 0.0 #need 2 calorie counters so I can add up both steps and basal calorie stuff
calories_from_hr = 0.0 #this creates a variable for us to count in our calories burned from heart rate using Male formula from Keytel paper
calories_per_step = 0.05 #calories_per_step is a made up number we assign to each step to get an estimated calorie count when multiplied by step count
start_time = None #start_time starts at 'None' so we can 'turn it on' when we are ready to dance!
tracking = False # tracking starts as false because we dont want the calorie counter to start until we are ready to dance (just like the timer)

#HR variables
bpm = 0 #creates a variable for our heart rate readings from BT monitor
hr_readings = [] #creates an array of heart rate readings to be used for calculating avg and max bpm
max_bpm = 0 #creats variable for the maximum BPM
average_bpm = 0 # lol similar to above but for average bpm
HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb" #This is a device specific code for the BT heart rate monitor i purchased
device_address = "F9:2D:CB:FD:CD:87" #specific address for BT device. If this gets lost use blue_tooth_find.py



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

def calculate_calories_per_second(hr, weight_kg, age):
    # Male formula (Keytel et al., 2005 https://pubmed.ncbi.nlm.nih.gov/15966347/ Worth a read!)
    calories_per_min = (-55.0969 + (0.6309 * hr) + (0.1988 * weight_kg) + (0.2017 * age)) / 4.184
    return max(calories_per_min / 60, 0)

#this function has a break down of how we want the timer to display time.
def update_timer():
    global calories_from_hr
    if tracking and start_time is not None:
        elapsed = int(time.time() - start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        timer_label.config(text=f"Time: {hrs:02}:{mins:02}:{secs:02}")

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
    if tracking:
        steps += 1
        calories_from_steps = steps * calories_per_step  # Only counts calories from steps with our made up magic number
        update_labels()

#this is what my start button activates when pressed! It begins the timer and step tracker
#***Do I want a pause button?
def start_tracking():
    global start_time, tracking
    steps = 0
    start_time = time.time()
    tracking = True
    update_labels()
    start_btn.config(state="disabled", bg="#666")


def get_stepmania_session_songs():
    try:
        stepmania_stats_path = os.path.expanduser(
            r"C:\Users\typec\AppData\Roaming\StepMania 5\Save\LocalProfiles\00000000\Stats.xml"
        )
        tree = ET.parse(stepmania_stats_path)
        root = tree.getroot()
        today = datetime.now().date()
        songs = []

        for song in root.findall(".//Song"):
            song_path = song.attrib.get("Dir", "Unknown Song")

            for steps in song.findall(".//Steps"):
                highscore_list = steps.find("HighScoreList")
                if highscore_list is None:
                    continue

                last_played_text = highscore_list.findtext("LastPlayed")
                if not last_played_text:
                    continue
                last_played = datetime.strptime(last_played_text, "%Y-%m-%d").date()
                if last_played != today:
                    continue

                highscore = highscore_list.find("HighScore")  # may be None
                difficulty = steps.attrib.get("Difficulty", "Unknown")
                score = highscore.findtext("Score") if highscore is not None else None
                duration = highscore.findtext("SurviveSeconds") if highscore is not None else None

                tap_scores = highscore.find("TapNoteScores") if highscore is not None else None
                miss = tap_scores.findtext("Miss") if tap_scores is not None else None
                boo = tap_scores.findtext("W5") if tap_scores is not None else None
                good = tap_scores.findtext("W4") if tap_scores is not None else None
                great = tap_scores.findtext("W3") if tap_scores is not None else None
                perfect = tap_scores.findtext("W2") if tap_scores is not None else None
                flawless = tap_scores.findtext("W1") if tap_scores is not None else None

                songs.append({
                    "song": os.path.basename(os.path.normpath(song_path)),
                    "difficulty": difficulty,
                    "score": score,
                    "duration": duration,
                    "last_played": last_played_text,
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
    if not tracking or start_time is None:
        messagebox.showinfo("Info", "No session data to save.")
        return

    elapsed = int(time.time() - start_time)
    hrs = elapsed // 3600
    mins = (elapsed % 3600) // 60
    secs = elapsed % 60
    duration = f"{hrs:02}:{mins:02}:{secs:02}"

    #where json lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(base_dir, "ddr_sessions")
    os.makedirs(save_dir, exist_ok=True)

    #file name: timestamped
    timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    default_name = f"DDR_Session_{timestamp}.json" 
    filename = os.path.join(save_dir, default_name)

    #get a data
    song_data = get_stepmania_session_songs()

    #step_rating_adder()

    biometrics_data = {
    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "steps": steps,
    "duration": duration,
    "average_bpm": average_bpm,
    "max_bpm": max_bpm,
    "calories": round(calories_from_hr + calories_from_steps, 2)
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
        session_steps_rating["flawless"] += int(song.get("flawless", 0))
        session_steps_rating["perfect"] += int(song.get("perfect", 0))
        session_steps_rating["great"] += int(song.get("great", 0))
        session_steps_rating["good"] += int(song.get("good", 0))
        session_steps_rating["boo"] += int(song.get("boo", 0))
        session_steps_rating["miss"] += int(song.get("miss", 0))

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
    accuracy = 100 * total_dance_steps / (
    total_dance_steps + session_steps_rating["miss"]
    )

    #adds the above count of total steps to json
    session_steps_rating["total_dance_steps"] = total_dance_steps
    session_steps_rating["accuracy"] = accuracy
    
    
    # jason data structure
    session_data = {
        "biometrics": biometrics_data,
        "songs": song_data,
        "session steps": session_steps_rating
    }

    # write to file
    try:
        with open(filename, "w") as f:
            json.dump(session_data, f, indent=4)
        messagebox.showinfo("Saved", f"Session saved to:\n{filename}")
    except Exception as error:
        messagebox.showerror("Error", f"Failed to save session:\n{error}")

#this prompts me on close if I want to save to JSON
def on_close():
    if tracking and start_time is not None:
        if messagebox.askyesno("Save Session", "Would you like to save your session as a CSV before exiting?"):
            save_to_json()
    root.destroy()

# GUI setup
root = tk.Tk()
root.title("DDR Step Tracker")
root.geometry("360x360")
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

# Labels
step_label = tk.Label(root, text="Steps: 0", font=("Helvetica", 24, "bold"),
                      bg=BG_GRADIENT, fg=ACCENT)
step_label.pack(pady=(20, 5))

calorie_label = tk.Label(root, text="Calories: 0.00", font=("Helvetica", 18),
                         bg=BG_GRADIENT, fg=TEXT_COLOR)
calorie_label.pack(pady=5)

timer_label = tk.Label(root, text="Time: 00:00:00", font=("Helvetica", 18),
                       bg=BG_GRADIENT, fg=TEXT_COLOR)
timer_label.pack(pady=5)

hr_label = tk.Label(root, text="Heart Rate: -- bpm", font=("Helvetica", 18),
                    bg=BG_GRADIENT, fg=TEXT_COLOR)
hr_label.pack(pady=5)

# Buttons
start_btn = tk.Button(root, text="Start", font=("Helvetica", 14, "bold"),
                      command=start_tracking, bg=ACCENT, fg="black",
                      activebackground="#d66fbe", activeforeground="white")
start_btn.pack(pady=10)

save_btn = tk.Button(root, text="Save to JSON", font=("Helvetica", 12),
                     command=save_to_json, bg="#dddddd", fg="black")
save_btn.pack(pady=5)

# Keyboard listeners (this will need to change when I get my DDR pad!)
for key in ['up', 'down', 'left', 'right']:
    keyboard.on_press_key(key, on_arrow_press)

#*** I should have a rescan check and also an indicator that BT is connected. It would stink to have a long session where I cant get HR data back
def start_ble_loop():
    async def run():
        try:
            async with BleakClient(device_address) as client:
                await client.start_notify(HR_MEASUREMENT_UUID, handle_hr_data)
                while True:
                    await asyncio.sleep(1)  # Keep connection alive
        except Exception as error:
            print(f"BLE Error: {error}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())

threading.Thread(target=start_ble_loop, daemon=True).start()


update_timer()
root.mainloop()