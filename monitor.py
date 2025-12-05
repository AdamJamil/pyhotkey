import pyautogui
from existing_state import ExistingState


def curr_monitor():
    pos = pyautogui.position()
    for m in ExistingState.monitors:
        if m.x <= pos[0] < m.x + m.width and m.y <= pos[1] < m.y + m.height:
            return m
