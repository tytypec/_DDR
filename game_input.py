import pygame
from inputs import get_gamepad

print("Listening for gamepad input...")

while True:
    events = get_gamepad()
    for event in events:
        print(event.ev_type, event.code, event.state)

# import keyboard

# def on_key(e):
#     print(f"Key pressed: {e.name}")

# keyboard.on_press(on_key)
# keyboard.wait()
#initialize pygame and joystick
# pygame.init()
# pygame.joystick.init()

# if pygame.joystick.get_count() == 0:
#     print("No joystick/gamepad detected.")
#     exit()

# joystick = pygame.joystick.Joystick(0)
# joystick.init()

# print(f"Detected joystick: {joystick.get_name()}")
# print("Press buttons on your DDR pad (Ctrl+C to quit)")

# while True:
#     for event in pygame.event.get():
#         if event.type == pygame.JOYBUTTONDOWN:
#             print(f"Button {event.button} pressed")


# def test_ltek_buttons():
#     import pygame
#     pygame.init()
#     pygame.joystick.init()

#     if pygame.joystick.get_count() == 0:
#         print("No joystick detected.")
#         return

#     joystick = pygame.joystick.Joystick(0)
#     joystick.init()
#     print(f"Testing input from: {joystick.get_name()}")

#     while True:
#         for event in pygame.event.get():
#             if event.type == pygame.JOYBUTTONDOWN:
#                 print(f"Button {event.button} pressed")
#             elif event.type == pygame.JOYHATMOTION:
#                 print(f"Hat moved to {event.value}")

# test_ltek_buttons()

