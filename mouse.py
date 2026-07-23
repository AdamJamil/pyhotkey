import math
import time
import pyautogui
from constants import RLT
from monitor import curr_monitor
from state import State

SLOW_MOUSE_SPEED = 4/15
FAST_MOUSE_SPEED = 4/5


def mouse_down(button):
    if not State.is_mouse_button_held(button):
        pyautogui.mouseDown(button=button)
    State.hold_mouse_button(button)


def mouse_up(button):
    State.release_mouse_button(button)
    pyautogui.mouseUp(button=button)


def mouse_move():
    last = time.perf_counter()
    base_speed = 25 * 100 / 3840  # percentage of screen per second

    while True:
        if not State.any_mouse_direction_held():
            break

        slow = RLT in State.get_held_modifiers()
        vx, vy = State.get_resultant_mouse_direction()
        mag = math.sqrt(vx * vx + vy * vy)

        if mag > 0:
            monitor = curr_monitor()
            if monitor is None:
                # cursor fell outside all known monitor rects (e.g. stale bounds
                # right after a resolution toggle); skip this tick, don't crash.
                last = time.perf_counter()
                time.sleep(0.001)
                continue
            px_per_s = monitor.width * base_speed
            speed = px_per_s * (SLOW_MOUSE_SPEED if slow else FAST_MOUSE_SPEED)
            dist = speed * (time.perf_counter() - last)
            scale = dist / mag
            pyautogui.moveRel(vx * scale, vy * scale)
        last = time.perf_counter()

        time.sleep(0.001)


def scroll_move():
    while True:
        if not State.any_scroll_direction_held():
            break

        vy = State.get_resultant_scroll_direction()
        mag = -vy * (30 if RLT not in State.get_held_modifiers() else 10)
        pyautogui.scroll(mag)

        time.sleep(0.01)


def mouse_jump(x, y):
    m = curr_monitor()
    if m is None:
        return
    pyautogui.moveTo(
        m.x + (x + 1) * m.width / 5,
        m.y + (y + 1) * m.height / 4,
    )


def mouse_toggle_screen():
    m = curr_monitor()
    if m is None:
        return
    pos = pyautogui.position()
    rel_x, rel_y = (pos[0] - m.x) / m.width, (pos[1] - m.y) / m.height
    monitors = State.monitors
    next_m = monitors[(monitors.index(m) + 1) % len(monitors)]
    pyautogui.moveTo(
        next_m.x + rel_x * next_m.width,
        next_m.y + rel_y * next_m.height,
    )
