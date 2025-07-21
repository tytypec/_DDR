import pygame
from inputs import get_gamepad

print("Listening for gamepad input...")

while True:
    events = get_gamepad()
    for event in events:
        print(event.ev_type, event.code, event.state)

