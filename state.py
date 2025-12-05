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

    # set of y values, one for each held key (just up/down), same as mouse
    __scroll_directions: Set[int] = set()
    _scroll_move_thread: Union[threading.Thread] = None

    # "left", "right", or "middle"
    __held_mouse_buttons: Set[str] = set()

    # this should take on values from MODIFIERS
    __held_modifiers: Set[str] = set()

    @staticmethod
    def init():
        State.update_monitors()

    @staticmethod
    def update_monitors():
        with State.lock:
            State.monitors = screeninfo.get_monitors()

    # ======================== Mouse button related methods ========================

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

    # ======================== Mouse movement related methods ========================

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

    # ======================== Scroll related methods ========================

    @staticmethod
    def add_scroll_direction(y: int):
        with State.lock:
            State.__scroll_directions.add(y)

    @staticmethod
    def remove_scroll_direction(y: int):
        with State.lock:
            if y in State.__scroll_directions:
                State.__scroll_directions.remove(y)

    @staticmethod
    def reset_scroll_direction():
        with State.lock:
            State.__scroll_directions = set()

    @staticmethod
    def any_scroll_direction_held() -> bool:
        with State.lock:
            return bool(State.__scroll_directions)

    @staticmethod
    def get_resultant_scroll_direction() -> int:
        with State.lock:
            if not State.__scroll_directions:
                return 0
            return sum(State.__scroll_directions)

    # ======================== Modifier related methods ========================

    @staticmethod
    def add_modifier(mod: str):
        with State.lock:
            State.__held_modifiers.add(mod)

    @staticmethod
    def remove_modifier(mod: str):
        with State.lock:
            if mod in State.__held_modifiers:
                State.__held_modifiers.remove(mod)

    @staticmethod
    def reset_modifiers():
        with State.lock:
            State.__held_modifiers = set()

    @staticmethod
    def get_held_modifiers() -> Set[str]:
        with State.lock:
            return set(State.__held_modifiers)


State.init()
