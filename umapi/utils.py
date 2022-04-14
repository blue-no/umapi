import os
from typing import Any, Dict
from datetime import datetime
import json


def abspath(relpath: str, origin: str) -> str:
    path_ = os.path.abspath(os.path.join(os.path.dirname(origin), relpath))
    return path_


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")


def formatted_now() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def read_json(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data

def write_json(data: Dict[str, Any], filepath: str) -> None:
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
