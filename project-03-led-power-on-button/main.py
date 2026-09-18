from signal import pause

from gpiozero import LED, Button
# import time

led = LED(17)
button = Button(26)

button.when_pressed = led.on # brings CPU usage down to 0.2% from 0.6% when using while loop
button.when_released = led.off

pause()  # This line is necessary to keep the program running and listening for button events.

# while True:
#     time.sleep(0.01) #this line can go here or at the end
#     if button.is_pressed:
#         led.on()
#     else:
#         led.off()   
     
#     # Before time.sleep(0.01) was added, the Task Manager showed 25% CPU usage.
#     # After adding time.sleep(0.01), the CPU usage dropped to 0.6% which is a significant improvement.
