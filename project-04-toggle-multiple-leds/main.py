from signal import pause
import time

from gpiozero import LED, Button
# import time

led_index = 0
led0 = LED(17)
led1 = LED(22)
led2 = LED(27)

led0.off()
led1.off()
led2.off()

button = Button(26, bounce_time=0.05)  # Set bounce_time to 0.1 seconds to prevent multiple triggers from a single press

def switch_led():
    global led_index
    if led_index == 0:
        led0.on()
        led2.off()
    elif led_index == 1:
        led1.on()
        led0.off()
    else:
        led2.on()
        led1.off()
        led_index = -1  # Reset index to -1 so that it becomes 0 after incrementing

    led_index += 1


button.when_pressed = switch_led # brings CPU usage down to 0.2% from 0.6% when using while loop

pause()  # This line is necessary to keep the program running and listening for button events.

# while True:
#     time.sleep(0.01) #this line can go here or at the end
#     if button.is_pressed:
#         led.on()
#     else:
#         led.off()   
     
#     # Before time.sleep(0.01) was added, the Task Manager showed 25% CPU usage.
#     # After adding time.sleep(0.01), the CPU usage dropped to 0.6% which is a significant improvement.
