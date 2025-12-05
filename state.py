import threading
from typing import List, Set, Tuple, Union
import screeninfo


class State:
    lock = threading.Lock()

    monitors: List[screeninfo.Monitor]

    # set of (x, y) tuples, one for each held key
    # private for thread safety
    __mouse_directions: Set[Tuple[int, int]] = set()
    _mouse_move_thread: Union[threading.Thread] = None

    @staticmethod
    def init():
        State.update_monitors()

    @staticmethod
    def update_monitors():
        with State.lock:
            State.monitors = screeninfo.get_monitors()

    @staticmethod
    def add_mouse_direction(x: int, y: int):
        with State.lock:
            State.__mouse_directions.add((x, y))

    @staticmethod
    def remove_mouse_direction(x: int, y: int):
        with State.lock:
            if (x, y) in State.__mouse_directions:
                State.__mouse_directions.remove((x, y))

    @staticmethod
    def reset_mouse_direction():
        with State.lock:
            State.__mouse_directions = set()

    @staticmethod
    def any_mouse_direction_held() -> bool:
        with State.lock:
            return bool(State.__mouse_directions)

    @staticmethod
    def get_resultant_mouse_direction() -> Tuple[int, int]:
        with State.lock:
            if not State.__mouse_directions:
                return (0, 0)
            return [sum(val) for val in zip(*State.__mouse_directions)]


State.init()
