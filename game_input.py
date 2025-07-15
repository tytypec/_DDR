import pygame

#initialize pygame and joystick
pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() == 0:
    print("No joystick/gamepad detected.")
    exit()

joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Detected joystick: {joystick.get_name()}")
print("Press buttons on your DDR pad (Ctrl+C to quit)")

while True:
    for event in pygame.event.get():
        if event.type == pygame.JOYBUTTONDOWN:
            print(f"Button {event.button} pressed")
