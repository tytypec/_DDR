##This is a simple utility for DDR so I can track play time AND some calories burned

import keyboard
import tkinter as tk
from tkinter import messagebox, filedialog
import time
import csv
from datetime import datetime
import os
import asyncio
from bleak import BleakClient

#steps creates a variable that we can count steps into.
#calories_per_step is a made up number we assign to each step to get an estimated calorie count when multiplied by step count
#start_time starts at 'None' so we can 'turn it on' when we are ready to dance!
# tracking starts as false because we dont want the calorie counter to start until we are ready to dance (just like the timer)
steps = 0
calories_per_step = 0.05
start_time = None
tracking = False
#HR variables
# HR_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
# address = "F9:2D:CB:FD:CD:87"
# BPM = 0

# GUI colors
BG_GRADIENT = "#6dcfff"
TEXT_COLOR = "#ffffff"
ACCENT = "#e754c2"

#this creates our text for our GUI elements. we have a step_label and a calorie_label
def update_labels():
    step_label.config(text=f"Steps: {steps}")
    calorie_label.config(text=f"Calories: {steps * calories_per_step:.2f}")

#this function has a break down of how we want the timer to display time.
def update_timer():
    if tracking and start_time is not None:
        elapsed = int(time.time() - start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        timer_label.config(text=f"Time: {hrs:02}:{mins:02}:{secs:02}")
    root.after(1000, update_timer)

#this takes an arrow press and adds a +1 into steps.
def on_arrow_press(event):
    global steps
    if tracking:
        steps += 1
        update_labels()

#this is what my start button activates when pressed! It begins the timer and step tracker
def start_tracking():
    global start_time, tracking
    steps = 0
    start_time = time.time()
    tracking = True
    update_labels()
    start_btn.config(state="disabled", bg="#666")

#This function allows me to save to .csv
def save_to_csv():
    if not tracking or start_time is None:
        messagebox.showinfo("Info", "No session data to save.")
        return

    elapsed = int(time.time() - start_time)
    hrs = elapsed // 3600
    mins = (elapsed % 3600) // 60
    secs = elapsed % 60
    duration = f"{hrs:02}:{mins:02}:{secs:02}"

    #Default directory: where the script lives
    base_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = os.path.join(base_dir, "ddr_sessions")
    os.makedirs(save_dir, exist_ok=True)

    #file name: timestamped
    timestamp = datetime.now().strftime("%Y-%m-%d-%H")
    default_name = f"DDR_Session_{timestamp}.csv"

    #File dialog with initial dir + name
    filename = filedialog.asksaveasfilename(
        initialdir=save_dir,
        initialfile=default_name,
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv")],
        title="Save session data"
    )
    if not filename:
        return

    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Steps", "Calories", "Duration"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            steps,
            f"{steps * calories_per_step:.2f}",
            duration
        ])
    messagebox.showinfo("Saved", f"Session saved to:\n{filename}")

#this prompts me on close if I want to save to CSV
def on_close():
    if tracking and start_time is not None:
        if messagebox.askyesno("Save Session", "Would you like to save your session as a CSV before exiting?"):
            save_to_csv()
    root.destroy()

# GUI setup
root = tk.Tk()
root.title("DDR Step Tracker")
root.geometry("360x360")
root.configure(bg=BG_GRADIENT)
root.protocol("WM_DELETE_WINDOW", on_close)  # Ask on close

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

# Buttons
start_btn = tk.Button(root, text="Start", font=("Helvetica", 14, "bold"),
                      command=start_tracking, bg=ACCENT, fg="black",
                      activebackground="#d66fbe", activeforeground="white")
start_btn.pack(pady=10)

save_btn = tk.Button(root, text="Save to CSV", font=("Helvetica", 12),
                     command=save_to_csv, bg="#dddddd", fg="black")
save_btn.pack(pady=5)

# Keyboard listeners (this will need to change when I get my DDR pad!)
for key in ['up', 'down', 'left', 'right']:
    keyboard.on_press_key(key, on_arrow_press)

update_timer()
root.mainloop()