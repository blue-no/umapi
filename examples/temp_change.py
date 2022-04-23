"""Example for controlling hotend temperature while printing."""

import random
from .utils import select_model
from umapi import *


def random_temp_change() -> None:
    temps = range(190, 235, 5)

    monitor = Monitor(savedir='tests')
    create_logger(savedir='tests', verbose=1)

    establish_connection()
    send_job(select_model())

    with monitor.start():
        monitor.wait_printstart()
        monitor.start_recording()

        for i in range(10):
            next_temp = random.choice(temps)
            change_hotendtemp(next_temp)
            monitor.wait_hotendtemp_reach(next_temp)
            print(f'{i}:\t{next_temp} [C]')


if __name__ == '__main__':
    random_temp_change()
