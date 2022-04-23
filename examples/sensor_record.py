"""Example for sensor values accumulation"""

from umapi import *


def record_sensor_values() -> None:
    monitor = Monitor(savedir='tests')
    create_logger(savedir='tests', verbose=1)

    establish_connection()

    with monitor.start():
        monitor.start_recording()
        time.sleep(10)


if __name__ == '__main__':
    record_sensor_values()
