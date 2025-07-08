#arrow_key_steps.py
import keyboard

steps = 0

print("Listening for arrow key presses... Press ESC to stop.")

def on_arrow_key(e):
    global steps
    steps += 1
    print(f"Steps: {steps}")

# Register all arrow keys
for key in ['up', 'down', 'left', 'right']:
    keyboard.on_press_key(key, on_arrow_key)

# Exit on ESC
keyboard.wait('esc')