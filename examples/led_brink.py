"""Example for led-brink of the printer"""

from umapi import *


def led_brink() -> None:
    establish_connection()

    for _ in range(5):
        change_brightness(0)
        time.sleep(1)
        change_brightness(100)
        time.sleep(1)


if __name__ == '__main__':
    led_brink()
