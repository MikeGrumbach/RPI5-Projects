from gpiozero import Button
import time

button = Button(26)

while True:
    print(button.is_pressed)
    time.sleep(1)