from collections import defaultdict as ddict, namedtuple
from functools import partial
import time
import threading
import math
from itertools import chain, combinations
import cli
from mouse import (
    mouse_down,
    mouse_jump,
    mouse_move,
    mouse_toggle_screen,
    mouse_up,
    scroll_move,
)
from state import State
from monitor import change_brightness, curr_monitor
from run_cmd import RunCMDThread
import os
import signal
import sys
import pathlib
import subprocess
import pyautogui
import screeninfo
from codeforces import put_code
from constants import (
    DEBUG_MODE,
    CAPS,
    RLT,
    RRT,
    LLT,
    MODIFIERS,
    OPEN_BRACKET,
    CLOSE_BRACKET,
)


import pywinauto.keyboard
from win32gui import GetWindowText, GetForegroundWindow


class KeyHandler:
    def __init__(self):
        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1

        self.done = False

        self.down_hotkeys = {
            (): {
                OPEN_BRACKET: "backspace",
                CLOSE_BRACKET: "delete",
            },
            (CAPS,): {
                "I": "up",
                "J": "left",
                "K": "down",
                "L": "right",
                "U": ["ctrl", "left"],
                "O": ["ctrl", "right"],
                "Y": "end",
                "H": "home",
                "A": [change_brightness, [0, 5]],
                "Z": [change_brightness, [0, -5]],
                "S": [change_brightness, [1, 5]],
                "X": [change_brightness, [1, -5]],
                "D": [change_brightness, [2, 5]],
                "C": [change_brightness, [2, -5]],
            },
            (RLT,): {
                "A": "[",
                "S": ["shift", "{"],
                "D": ["shift", "("],
                "F": "\\",
                "G": "+",
                "T": "_",
                "Y": "=",
                "H": "-",
                "J": "/",
                "K": ["shift", ")"],
                "L": ["shift", "}"],
                "Oem_1": "]",
                "Q": "volumemute",
                "W": "volumedown",
                "E": "volumeup",
            },
            (CAPS, RLT): {
                "I": ["shift", "up"],
                "J": ["shift", "left"],
                "K": ["shift", "down"],
                "L": ["shift", "right"],
                "U": ["ctrl", "shift", "left"],
                "O": ["ctrl", "shift", "right"],
                "Y": ["shift", "end"],
                "H": ["shift", "home"],
            },
            (RRT,): {
                "E": [self.mouse_key_add, [(0, -1)]],
                "S": [self.mouse_key_add, [(-1, 0)]],
                "D": [self.mouse_key_add, [(0, 1)]],
                "F": [self.mouse_key_add, [(1, 0)]],
                "R": [mouse_down, ["left"]],
                "3": [mouse_down, ["middle"]],
                "W": [mouse_down, ["right"]],
                # "T": [pyautogui.scroll, [-3]],
                # "G": [pyautogui.scroll, [3]],
                "H": mouse_toggle_screen,
                "T": [self.scroll_key_add, [-1]],
                "G": [self.scroll_key_add, [1]],
            },
            (RLT, RRT,): {
                "E": [self.mouse_key_add, [(0, -1)]],
                "S": [self.mouse_key_add, [(-1, 0)]],
                "D": [self.mouse_key_add, [(0, 1)]],
                "F": [self.mouse_key_add, [(1, 0)]],
                "R": [mouse_down, ["left"]],
                "3": [mouse_down, ["middle"]],
                "W": [mouse_down, ["right"]],
                # "T": [pyautogui.scroll, [-3]],
                # "G": [pyautogui.scroll, [3]],
                "H": mouse_toggle_screen,
                "T": [self.scroll_key_add, [-1]],
                "G": [self.scroll_key_add, [1]],
            },
            (LLT,): {
                "E": [mouse_down, ["left"]],
                "2": [mouse_down, ["middle"]],
                "Q": [mouse_down, ["right"]],
                # "W": [pyautogui.scroll, [-6]],
                # "S": [pyautogui.scroll, [6]],
                "W": [self.scroll_key_add, [-1]],
                "S": [self.scroll_key_add, [1]],
            },
            (CAPS, RLT, RRT): {
                "Q": self.exit,
                "R": self.restart,
            },
        }

        self.up_hotkeys = {
            (RRT,): {
                "E": [self.mouse_key_remove, [(0, -1)]],
                "S": [self.mouse_key_remove, [(-1, 0)]],
                "D": [self.mouse_key_remove, [(0, 1)]],
                "F": [self.mouse_key_remove, [(1, 0)]],
                "R": [mouse_up, ["left"]],
                "3": [mouse_up, ["middle"]],
                "W": [mouse_up, ["right"]],
                "T": [self.scroll_key_remove, [-1]],
                "G": [self.scroll_key_remove, [1]],
            },
            (RLT, RRT,): {
                "E": [self.mouse_key_remove, [(0, -1)]],
                "S": [self.mouse_key_remove, [(-1, 0)]],
                "D": [self.mouse_key_remove, [(0, 1)]],
                "F": [self.mouse_key_remove, [(1, 0)]],
                "R": [mouse_up, ["left"]],
                "3": [mouse_up, ["middle"]],
                "W": [mouse_up, ["right"]],
                "T": [self.scroll_key_remove, [-1]],
                "G": [self.scroll_key_remove, [1]],
            },
            (LLT,): {
                "E": [mouse_up, ["left"]],
                "2": [mouse_up, ["middle"]],
                "Q": [mouse_up, ["right"]],
                "W": [self.scroll_key_remove, [-1]],
                "S": [self.scroll_key_remove, [1]],
            },
        }

        # TODO: sort the order of the modifier keys

        jump_keys = [
            ["U", "I", "O", "P"],
            ["J", "K", "L", "Oem_1"],
            ["M", "Oem_Comma", "Oem_Period", "Oem_2"],
        ]
        jump_map = {
            key: [y, x] for x, row in enumerate(jump_keys) for y, key in enumerate(row)
        }
        for char in jump_map.keys():
            self.down_hotkeys[RRT,][char] = [mouse_jump, jump_map[char]]

        # allow for repetition
        for i in range(1, 10):
            self.down_hotkeys[CAPS,][str(i)] = [
                partial(self.__setattr__, "rep"),
                [i],
            ]

        # TODO: reimplement this
        # # hard reset check (double press esc)
        # for key in self.down_hotkeys.keys():
        #     self.down_hotkeys[key]["Escape"] = [self.esc_check, []]

    def key_down(self, event):
        """
        Returns True if the event should be passed to the OS, False otherwise.
        """
        if time.time() - self.last_press < 0.001:
            return True

        if event.Key in MODIFIERS:
            State.add_modifier(event.Key)
            return False

        modifiers = tuple(sorted(State.get_held_modifiers()))
        if modifiers not in self.down_hotkeys:
            return True  # TODO: implement partial matching

        action = self.down_hotkeys[modifiers].get(event.Key, None)
        if action is None:
            return True

        if isinstance(action, str):
            self.press(action)

        elif isinstance(action, list) and all(isinstance(a, str) for a in action):
            self.press(*action)

        elif isinstance(action, list):  # in this case, it's a [func, args] pair
            action[0](*action[1])

        else:  # it's a single function with no args
            action()

        return False

    def key_up(self, event):
        if event.Key in MODIFIERS:
            State.remove_modifier(event.Key)

            if event.Key == CAPS:
                self.reset()
            elif event.Key in (RRT, LLT):
                self.mouse_reset()

            return False

        modifiers = tuple(sorted(State.get_held_modifiers()))
        if modifiers not in self.up_hotkeys:
            return True  # TODO: implement partial matching

        action = self.up_hotkeys[modifiers].get(event.Key, None)
        if action is None:
            return True

        if isinstance(action, list):  # in this case, it's a [func, args] pair
            action[0](*action[1])

        else:  # it's a single function with no args
            action()

        if DEBUG_MODE:
            print(event, State.get_held_modifiers())
        return False

    pywinmap = {
        "{": "+[",
        "}": "+]",
        "(": "{(}",
        ")": "{)}",
        "+": "{+}",
        "_": "{_}",
    }

    def press(self, *keys):
        if DEBUG_MODE:
            print(f"pressing {keys}")

        for _ in range(self.rep):
            self.last_press = time.time()
            for k in keys:
                pyautogui.keyDown(k)
            for k in reversed(keys):
                pyautogui.keyUp(k)

        if DEBUG_MODE:
            print(f"done pressing {keys}")

        self.rep = 1

    def reset(self):
        if DEBUG_MODE:
            print("reset")
        self.rep = 1
        State.remove_modifier(CAPS)
        self.LMB_held = False
        State.update_monitors()

        return True

    def mouse_reset(self):
        State.LMB_held = False
        State.reset_mouse_direction()
        State.reset_scroll_direction()
        for mod in (LLT, RRT):
            State.remove_modifier(mod)
        return True

    def hard_reset(self):
        self.last_press = time.time()
        self.last_esc = time.time()
        self.rep = 1
        State.reset_modifiers()
        self.mouse_reset()
        self.reset()
        return True

    def esc_check(self):
        if time.time() - self.last_esc < 0.5:
            self.hard_reset()
        self.last_esc = time.time()
        return True

    def mouse_key_add(self, key):
        State.add_mouse_direction(*key)

        if State._mouse_move_thread is None:
            State._mouse_move_thread = threading.Thread(target=mouse_move, daemon=True)
            State._mouse_move_thread.start()

    def mouse_key_remove(self, key):
        print("removing", key)
        State.remove_mouse_direction(*key)
        if not State.any_mouse_direction_held():
            print("stopping mouse thread")
            State._mouse_move_thread = None

    def scroll_key_add(self, key):
        State.add_scroll_direction(key)

        if State._scroll_move_thread is None:
            State._scroll_move_thread = threading.Thread(
                target=scroll_move, daemon=True
            )
            State._scroll_move_thread.start()

    def scroll_key_remove(self, key):
        State.remove_scroll_direction(key)
        if not State.any_scroll_direction_held():
            State._scroll_move_thread = None

    def exit(self):
        if self.done:
            return
        self.done = True

        # if self.alarm_clock:
        #     self.alarm_clock.save()

        threading.Timer(0.1, lambda: os._exit(0)).start()

    def restart(self):
        subprocess.Popen([sys.executable] + sys.argv, close_fds=True)
        self.exit()
