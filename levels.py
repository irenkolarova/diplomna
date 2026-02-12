import gpiod
import time

MAGNET_PIN = 5      
BTN_TOGGLE = 22
BTN_LEVEL  = 24

chip = gpiod.Chip('gpiochip4')

magnet = chip.get_line(MAGNET_PIN)
btn_toggle = chip.get_line(BTN_TOGGLE)
btn_level  = chip.get_line(BTN_LEVEL)

magnet.request(
    consumer='magnet',
    type=gpiod.LINE_REQ_DIR_OUT,
    default_val=0
)

btn_toggle.request(
    consumer='btn_toggle',
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
)

btn_level.request(
    consumer='btn_level',
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
)

magnet_on = False
level = 1            # 1 = 100%, 2 = 40%

last_toggle = 1
last_level  = 1

PWM_PERIOD = 0.01    

def magnet_pwm(on, duty):
    if not on:
        magnet.set_value(0)
        time.sleep(PWM_PERIOD)
        return

    on_time  = PWM_PERIOD * duty
    off_time = PWM_PERIOD * (1 - duty)

    magnet.set_value(1)
    time.sleep(on_time)
    magnet.set_value(0)
    time.sleep(off_time)

try:
    while True:
        t = btn_toggle.get_value()
        if last_toggle == 1 and t == 0:
            magnet_on = not magnet_on
            time.sleep(0.25)
        last_toggle = t

        l = btn_level.get_value()
        if last_level == 1 and l == 0:
            level = 2 if level == 1 else 1
            time.sleep(0.25)
        last_level = l

        if level == 1:
            duty = 1.0      
        else:
            duty = 0.4     

        magnet_pwm(magnet_on, duty)

except KeyboardInterrupt:
    pass

finally:
    magnet.set_value(0)
    magnet.release()
    btn_toggle.release()
    btn_level.release()
