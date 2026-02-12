import gpiod
import time

chip = gpiod.Chip('gpiochip4')
btn = chip.get_line(22)

btn.request(
    consumer='btn_test',
    type=gpiod.LINE_REQ_DIR_IN,
    flags=gpiod.LINE_REQ_FLAG_BIAS_PULL_UP
)

while True:
    print(btn.get_value())
    time.sleep(0.3)
