"""Example for sending and printing model via program."""

from .utils import select_model
from umapi import *


def print_model(model_path: str) -> None:
    establish_connection()
    send_job(model_path)


if __name__ == '__main__':
    print_model(select_model())
