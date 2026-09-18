from gpiozero import LED, Button
import time

led = LED(17)
button = Button(26)

while True:
    time.sleep(0.01)
    if button.is_pressed:
        led.on()
    else:
        led.off()   
     
    # Before time.sleep(0.01) was added, the Task Manager showed 25% CPU usage.
    # After adding time.sleep(0.01), the CPU usage dropped to 0.6% which is a significant improvement.
