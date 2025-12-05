import pyautogui
from state import State


def curr_monitor():
    pos = pyautogui.position()
    for m in State.monitors:
        if m.x <= pos[0] < m.x + m.width and m.y <= pos[1] < m.y + m.height:
            return m
