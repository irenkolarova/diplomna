import gpiod
import time


ControlPin = [14, 15, 18, 23]

BTN_RIGHT = 17
BTN_LEFT  = 27

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

delay = 0.001
step = 0

try:
    while True:
        right_pressed = (btn_r.get_value() == 0)
        left_pressed  = (btn_l.get_value() == 0)

        if right_pressed and not left_pressed:
            pattern = seg_right[step % 8]
            step += 1

        elif left_pressed and not right_pressed:
            pattern = seg_left[step % 8]
            step += 1

        else:
            for line in motor_lines:
                line.set_value(0)
            time.sleep(0.01)
            continue

        for i in range(4):
            motor_lines[i].set_value(pattern[i])

        time.sleep(delay)

except KeyboardInterrupt:
    pass

finally:
    for line in motor_lines:
        line.set_value(0)
        line.release()
    btn_r.release()
    btn_l.release()