import gpiod
import time

ControlPin = [14, 15, 18, 23]

BTN_RIGHT = 17
BTN_LEFT  = 27

MAGNET_PIN = 5     
BTN_MAGNET = 22    

delay = 0.001          
debounce_s = 0.03      

chip = gpiod.Chip('gpiochip4')

motor_lines = [chip.get_line(pin) for pin in ControlPin]
for line in motor_lines:
    line.request(
        consumer='stepper_motor',
        type=gpiod.LINE_REQ_DIR_OUT,
        default_val=0
    )

btn_r = chip.get_line(BTN_RIGHT)
btn_l = chip.get_line(BTN_LEFT)
btn_m = chip.get_line(BTN_MAGNET)

btn_r.request(
    consumer='btn_right',
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
)
btn_l.request(
    consumer='btn_left',
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
)
btn_m.request(
    consumer='btn_magnet',
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
)

magnet = chip.get_line(MAGNET_PIN)
magnet.request(
    consumer='electromagnet',
    type=gpiod.LINE_REQ_DIR_OUT,
    default_val=0
)

magnet_state = 0
magnet.set_value(0)

seg_right = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

seg_left = [
    [0,0,0,1],
    [0,0,1,1],
    [0,0,1,0],
    [0,1,1,0],
    [0,1,0,0],
    [1,1,0,0],
    [1,0,0,0],
    [1,0,0,1]
]

step = 0

def motor_stop():
    for line in motor_lines:
        line.set_value(0)

def toggle_magnet():
    global magnet_state
    magnet_state ^= 1
    magnet.set_value(magnet_state)

try:
    while True:
        if btn_m.get_value() == 0:           
            time.sleep(debounce_s)          
            if btn_m.get_value() == 0:      
                toggle_magnet()
                while btn_m.get_value() == 0:
                    time.sleep(0.01)

        right_pressed = (btn_r.get_value() == 0)
        left_pressed  = (btn_l.get_value() == 0)

        if right_pressed and not left_pressed:
            pattern = seg_right[step % 8]
            step += 1
            for i in range(4):
                motor_lines[i].set_value(pattern[i])
            time.sleep(delay)

        elif left_pressed and not right_pressed:
            pattern = seg_left[step % 8]
            step += 1
            for i in range(4):
                motor_lines[i].set_value(pattern[i])
            time.sleep(delay)

        else:
            motor_stop()
            time.sleep(0.005)

except KeyboardInterrupt:
    pass

finally:
    motor_stop()
    for line in motor_lines:
        line.release()

    magnet.set_value(0)
    magnet.release()

    btn_r.release()
    btn_l.release()
    btn_m.release()
